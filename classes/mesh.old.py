from logger import Logger
from product import Product
from variant import Variant
from time import time, sleep
import json
import requests

log = Logger().log


class Mesh:
    def __init__(self):
        with open('config.json') as config:
            self.settings = json.load(config)
        self.start = time()  # For timing purposes
        # item settings
        self.keywords = self.settings['product']['positive_kw'].split(',')  # Positive keywords (must match all keywords)
        self.negatives = self.settings['product']['negative_kw'].split(',')  # Negative keywords (matching any of these discards item)
        self.size = self.settings['product']['size']
        if self.settings['site'] == 'FP':
            self.api_key = '5F9D749B65CD44479C1BA2AA21991925'
            self.user_agent = 'FootPatrol/2.0 CFNetwork/808.3 Darwin/16.3.0'
            self.cart_id = self.settings['cart_ids']['fp_id']
            self.sitename = 'footpatrol'
        elif self.settings['site'] == 'JD':
            self.api_key = '1A17CC86AC974C8D9047262E77A825A4'
            self.user_agent = 'JDSports/5.3.1.207 CFNetwork/808.3 Darwin/16.3.0'
            self.cart_id = self.settings['cart_ids']['jd_id']
            self.sitename = 'jdsports'
        elif self.settings['site'] == 'SZ':
            self.api_key = 'EA0E72B099914EB3BA6BE90A21EA43A9'
            self.user_agent = 'Size-APPLEPAY/4.0 CFNetwork/808.3 Darwin/16.3.0'
            self.cart_id = self.settings['cart_ids']['sz_id']
            self.sitename = 'size'
        else:
            log("[error] defining Mesh object with site {}".format(self.settings['site']))
            exit(-1)

        self.products = []  # List for storing scraped products
        self.matches = []  # Matching product list. Proceed if we only find one (or pick)
        self.variants = []  # List of product variants (in case size is sold out)
        # customer settings
        self.customer_id = None  # Stored for checkout
        self.address_id = None  # Stored for checkout
        self.callback_url = None  # Stored for checkout
        self.delivery_id = None  # Stored for checkout
        self.hps_id = None  # Stored for checkout
        self.s = requests.Session()
        log("MeshAPI by Luke Davis (@R8T3D)")
        log("ATC by Alex Gompper (@573supreme/@edzart)")
        print
        log("[init] key: {}".format(self.api_key))
        log("[init] user-agent: {}".format(self.user_agent))

        self.headers = {
            'Host': 'commerce.mesh.mx',
            'Content-Type': 'application/json',
            'X-API-Key': self.api_key,
            'Accept': '*/*',
            'X-Debug': '1',
            'Accept-Language': 'en-gb',
            'User-Agent': self.user_agent,
            'MESH-Commerce-Channel': 'iphone-app',
        }

    def build_product_list(self):
        log("[products] building product list")
        try:
            max = 2000
            if self.settings['site'] == 'JD':
                params = {
                    "from": 0,
                    "max": max,
                    "channel": "iphone-app"
                }
                url = "https://commerce.mesh.mx/stores/jdsports/products/category/men/mens-footwear"
            elif self.settings['site'] == 'FP':
                params = {
                    "from": 0,
                    "max": max,
                    "channel": "iphone-app"

                }
                url = "https://commerce.mesh.mx/stores/footpatrol/products/category/footwear/all-footwear"
            else:
                params = {
                    "from": 0,
                    "max": max,
                    "channel": "iphone-app"
                }
                url = "https://commerce.mesh.mx/stores/size/products/category/mens/footwear"
            r = requests.request(
                'GET',
                url,
                params=params,
                headers=self.headers
            )
            if r.status_code != 200:
                log("[error] got bad status code {} from scrape request".format(r.status_code))
                print r.text
                return False
            else:
                try:
                    r = r.json()
                    for prod in r['products']:
                        name = prod['name'].encode('utf-8').strip()
                        try:
                            name = "{} {}".format(name, prod['colour'])
                        except KeyError:
                            name = prod['name']
                        log("[prod] {} \t {} \t {}".format(prod['stockStatus'].encode('utf-8').strip(),
                                                           prod['SKU'].encode('utf-8').strip(), name))
                        p = Product(
                            prod['SKU'].encode('utf-8').strip(),
                            name,
                            prod['stockStatus'].encode('utf-8').strip()
                        )
                        self.products.append(p)
                    log("[products] found {} products".format(len(r['products'])))
                    return True
                except KeyError:
                    log("[error] key error while processing product list json")
                    return False
        except UnicodeEncodeError:
            log("[error] unicode error on build product request")
            return False

    def check_product_list(self):
        log("[products] checking product list")
        for p in self.products:
            match = True
            for neg in self.negatives:
                if neg in p.name:
                    match = False
            for key in self.keywords:
                if key not in p.name:
                    match = False
            if match:
                self.matches.append(p)
                log("[match] found a match {} \t {}".format(p.sku, p.name))
        if len(self.matches) >= 1:
            log("[matches] found {} matching item(s)".format(len(self.matches)))
            return True
        else:
            log("[error] no matches found")
            return False

    def get_product_info(self):
        log("[prod] retrieving product info for SKU {}".format(self.matches[0].sku))
        try:
            params = {
                "expand": "variations,informationBlocks,customisations",
                "channel": "iphone-app"
            }
            url = "https://commerce.mesh.mx/stores/{}/products/{}".format(self.sitename, self.matches[0].sku)
            r = requests.request(
                'GET',
                url,
                headers=self.headers,
                params=params
            )
            if r.status_code != 200:
                log("[error] got bad status code {} from product info request".format(r.status_code))
                print r.text
                return False
            else:
                r = r.json()
                for size in r['options']:
                    log("[size] {}  \t sku {} \t {}".format(
                        size,
                        r['options'][size]['SKU'],
                        r['options'][size]['stockStatus']
                    ))
                    v = Variant(
                        size,
                        r['options'][size]['SKU'],
                        r['options'][size]['stockStatus']
                    )
                    self.variants.append(v)
                return True
        except KeyError:
            log("[error] exception while getting product info json")
            return False

    def sel_product_sku(self):
        log("[prod] scanning product info for size")
        for var in self.variants:
            if var.size == self.size:
                log("[match] found a matching size {} with sku {}".format(var.size, var.sku))
                self.settings['product']['preset_sku'] = var.sku
                return True
        log("[error] didnt find a matching size {}".format(self.size))
        return False

    def add_to_cart(self):
        log("[atc] adding product to cart")
        if self.cart_id is None:
            log("[POST METHOD] (not using predefined cart ID)")
            if self.settings['site'] == 'JD':
                url = "https://commerce.mesh.mx/stores/jdsports/carts"
                payload = {
                    "channel": "iphone-app",
                    "contents": [{
                        "$schema": "https://commerce.mesh.mx/stores/jdsports/schema/CartProduct",
                        "SKU": self.settings['product']['preset_sku'],
                        "quantity": 1
                    }]
                }
            else:
                url = "https://commerce.mesh.mx/stores/{}/carts".format(self.sitename)
                payload = {
                    "channel": "iphone-app",
                    "products": [{
                        "SKU": self.settings['product']['preset_sku'],
                        "quantity": 1
                    }]
                }
            r = self.s.request(
                'POST',
                url,
                headers=self.headers,
                json=payload
            )
            if r.status_code is 201:
                r = r.json()
                log("[cart] got good status code from post request")
                self.cart_id = r['ID']
                log("[cart] new cart id {}".format(self.cart_id))
                return True
            else:
                log("[error] got bad status code {} from post request".format(r.status_code))
                print r.text
                return False
        else:  # if we have a predefined cart ID, use it + PUT method
            log("[PUT METHOD] (using predefined cart ID)")
            if self.settings['site'] == 'JD':
                url = 'https://commerce.mesh.mx/stores/jdsports/carts/' + self.cart_id
                data = {
                    "contents": [{
                        "$schema": "https://commerce.mesh.mx/stores/jdsports/schema/CartProduct",
                        "SKU": self.settings['product']['preset_sku'],
                        "quantity": 1
                    }]
                }
            else:
                url = 'https://commerce.mesh.mx/stores/' + self.sitename + '/carts/' + self.cart_id + '/' + self.settings['product']['preset_sku']
                data = {
                    "quantity": 1
                }
            r = self.s.request(
                'PUT',
                url,
                headers=self.headers,
                json=data
            )
            if (r.status_code >= 200) and (r.status_code < 210):
                log("[cart] got good status code from put request")
                return True
            else:
                log("[error] got bad status code {} from put request".format(r.status_code))
                print r.text
                return False

    def create_customer(self):
        log("[customer] creating customer and address ID")
        url = "https://commerce.mesh.mx/stores/{}/customers".format(self.sitename)
        data = {
            "phone": self.settings['checkout']['phone'],
            "gender": "",
            "firstName": self.settings['checkout']['fname'],
            "addresses": [{
                "locale": "us",
                "county": self.settings['checkout']['state'],
                "country": "United States",
                "address1": self.settings['checkout']['addr1'],
                "town": self.settings['checkout']['city'],
                "postcode": self.settings['checkout']['zip'],
                "isPrimaryBillingAddress": True,
                "isPrimaryAddress": True,
                "address2": self.settings['checkout']['addr2']
            }],
            "title": "",
            "email": self.settings['checkout']['email'],
            "isGuest": True,
            "lastName": self.settings['checkout']['lname']
        }
        r = self.s.request(
            'POST',
            url,
            headers=self.headers,
            json=data
        )
        if r.status_code is 200 or 201:
            log("[customer] got good status code from customer creation post")
            r = r.json()
            try:
                self.customer_id = r['ID']
                self.address_id = r['addresses'][0]['ID']
                log("[customer] got customer id {}".format(self.customer_id))
                log("[customer] got address id {}".format(self.address_id))
            except KeyError:
                log("[error] key error when parsing customer response json")
                return False
        else:
            log("[error] got bad status code {} from customer creation post".format(r.status_code))
            print r.text
            return False

    def submit_ids(self):
        url = "https://commerce.mesh.mx/stores/{}/carts/{}".format(self.sitename, self.cart_id)
        if self.settings['site'] is 'JD':
            data = {
                "id": "https:\\/\\/commerce.mesh.mx\\/stores\\/jdsports\\/carts\\/{}".format(self.cart_id),
                "customer": {
                    "id": "https:\\/\\/commerce.mesh.mx\\/stores\\/jdsports\\/customers\\/{}".format(self.customer_id)
                },
                "billingAddress": {
                    "id": "https:\\/\\/commerce.mesh.mx\\/stores\\/jdsports\\/customers\\/{}\/addresses\\/{}".format(
                        self.customer_id,
                        self.address_id
                    )
                },
                "deliveryAddress": {
                    "id": "https:\\/\\/commerce.mesh.mx\\/stores\\/jdsports\\/customers\\/{}\\/addresses\\/{}".format(
                        self.customer_id,
                        self.address_id
                    )
                }
            }
        else:
            data = {
                "customerID": self.customer_id,
                "billingAddressID": self.address_id,
                "deliveryAddressID": self.address_id
            }
        r = self.s.request(
            'PUT',
            url,
            headers=self.headers,
            json=data
        )
        if r.status_code is 200:
            log("[ids] got good response code from customer id post")
            try:
                r = r.json()
                self.delivery_id = r['deliveryOptions'][0]['ID']
                log("[ids] found delivery id {}".format(self.delivery_id))
            except KeyError:
                log("[erorr] key error while parsing customer json")
                return False
        else:
            log("[error] got bad status code {} from customer id post".format(r.status_code))
            print r.text
            return False

    def start_hosted_payment(self):
        log("[payment] starting hosted payment")
        url = "https://commerce.mesh.mx/stores/{}/carts/{}/hostedPayment".format(self.sitename, self.cart_id)
        data = {
            "type": "CARD",
            "terminals": {
                "successURL": "https://ok",
                "failureURL": "https://fail",
                "timeoutURL": "https://timeout"
            }
        }
        r = self.s.request(
            'POST',
            url,
            headers=self.headers,
            json=data
        )
        if r.status_code is 200:
            log("[payment] got good status code from hosted payment post")
            try:
                r = r.json()
                self.callback_url = r['href']
                self.hps_id = r['terminalEndPoints']['hostedPageURL'].split('HPS_SessionID=')[1]
                log("[ids] found payment callback {}".format(self.callback_url))
                log("[ids] found hps session id {}".format(self.hps_id))
                return True
            except KeyError:
                log("[error] key error while parsing hosted payment json")
                print r.text
                return False
        else:
            log("[payment] got bad status code {} from hosted payment post".format(r.status_code))
            print r.text
            return False

    def submit_card(self):
        log("[card] grabbing card session cookie")
        url = "https://hps.datacash.com/hps/?HPS_SessionID={}".format(self.hps_id)
        headers = {
            "Host": "hps.datacash.com",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_2 like Mac OS X) AppleWebKit/603.2.4 (KHTML, like Gecko) Mobile/14F89",
            "Accept-Language": "en-us",
            "Accept-Encoding": "gzip,deflate"
        }
        r = self.s.request(
            'GET',
            url,
            headers=headers
        )
        if r.status_code is 200:
            log("[card] got good status code from hps get")
        else:
            log("[error] got bad status code {} from hps get".format(r.status_code))
            return False
        log("[card] submitting card info")
        url = "https://hps.datacash.com/hps/"
        data = {
            "card_number": self.settings['checkout']['cc'],
            "exp_month": self.settings['checkout']['exp_m'],
            "exp_year": self.settings['checkout']['exp_y'],
            "cv2_number": self.settings['checkout']['cvv'],
            "issue_number": "",
            "HPS_SessionID": self.hps_id,
            "action": "confirm",
            "continue": ""
        }
        headers = {
            "Host": "hps.datacash.com",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://hps.datacash.com",
            "Connection": "keep-alive",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_2 like Mac OS X) AppleWebKit/603.2.4 (KHTML, like Gecko) Mobile/14F89",
            "Referer": "https://hps.datacash.com/hps/?HPS_SessionID={}".format(self.hps_id),
            "Accept-Language": "en-us",
            "Accept-Encoding": "gzip,deflate"
        }
        try:
            r = self.s.request(
                'POST',
                url,
                headers=headers,
                data=data,
                allow_redirects=False
            )
        except requests.exceptions.ProxyError:
            log("[error] redirect problem")
            print r.url
            print r.headers
            return False
        # if r.status_code is not 200:
        #     print r.url
        #     print r.headers
        #     log("[error] bad status code {} from card info post".format(r.status_code))
        #     return False
        # if "error_message" in r.content:
        #     log("[error] encountered error while posting card info")
        #     print r.text
        #     return False
        # else:
        payment_token = r.headers['Location']
        log("[card] successfully submitted card info")
        log("[callback] firing payment callback")
        data = {
            "HostedPaymentPageResult": payment_token
        }
        r = self.s.request(
            'POST',
            self.callback_url + '/hostedpaymentresult',
            headers=self.headers,
            data=data
        )
        print r.text

    def checkout(self):
        log("[checkout] check out not fully implemented yet - use at your own risk")
        self.create_customer()
        self.submit_ids()
        if self.start_hosted_payment():
            self.submit_card()
