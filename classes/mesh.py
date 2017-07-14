from logger import Logger
from product import Product
from variant import Variant
from time import time
import json
import requests
log = Logger().log


class Mesh:
    def __init__(self, site):

        with open('config.json') as config:
            self.settings = json.load(config)

        self.site = site
        self.start = time()  # For timing purposes
        # Cart tokens should be replaced before each drop. Sniff the iOS traffic to pick a new one by adding a bs
        # item to your cart, collecting the ID from the PUT request and replacing them below. JD has a method to not
        # use a pre-defined cart ID but I still recommend picking a new one before each drop
        self.fp_cart_id = self.settings['cart_ids']['fp_id']  # Footpartrol cart ID. Cannot be none.
        self.sz_cart_id = self.settings['cart_ids']['sz_id']  # Size? cart ID. Leave none to start a new cart
        self.jd_cart_id = self.settings['cart_ids']['jd_id']  # JD Sports cart ID. Leave none to start new cart.
        self.skupid = self.settings['product']['preset_sku']  # If we find a hit item, store PID here (or set to something else to jump to atc)
        # item settings
        self.keywords = self.settings['product']['positive_kw'].split(',')  # Positive keywords (must match all keywords)
        self.negatives = self.settings['product']['negative_kw'].split(',')  # Negative keywords (matching any of these discards item)
        self.size = self.settings['product']['size']
        if self.site == 'FP':
            self.api_key = '5F9D749B65CD44479C1BA2AA21991925'
            self.user_agent = 'FootPatrol/2.0 CFNetwork/808.3 Darwin/16.3.0'
            self.cart_id = self.fp_cart_id
            self.sitename = 'footpatrol'
        elif self.site == 'JD':
            self.api_key = '1A17CC86AC974C8D9047262E77A825A4'
            self.user_agent = 'JDSports/5.3.1.207 CFNetwork/808.3 Darwin/16.3.0'
            self.cart_id = self.jd_cart_id
            self.sitename = 'jdsports'
        elif self.site == 'SZ':
            self.api_key = 'EA0E72B099914EB3BA6BE90A21EA43A9'
            self.user_agent = 'Size-APPLEPAY/4.0 CFNetwork/808.3 Darwin/16.3.0'
            self.cart_id = self.sz_cart_id
            self.sitename = 'size'
        else:
            log("[error] defining Mesh object with site {}".format(site))
            exit(-1)

        self.products = []  # List for storing scraped products
        self.matches = []  # Matching product list. Proceed if we only find one (or pick)
        self.variants = []  # List of product variants (in case size is sold out)
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
            if self.site == 'JD':
                params = {
                    "from": 0,
                    "max": max,
                    "channel": "iphone-app"
                }
                url = "https://commerce.mesh.mx/stores/jdsports/products/category/men/mens-footwear"
            elif self.site == 'FP':
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
            ).json()
            for prod in r['products']:
                name = prod['name'].encode('utf-8').strip()
                try:
                    name = "{} {}".format(name, prod['colour'])
                except KeyError:
                    name = prod['name']
                log("[prod] {} \t {} \t {}".format(prod['stockStatus'].encode('utf-8').strip(), prod['SKU'].encode('utf-8').strip(), name))
                p = Product(
                    prod['SKU'].encode('utf-8').strip(),
                    name,
                    prod['stockStatus'].encode('utf-8').strip()
                )
                self.products.append(p)
            log("[products] found {} products".format(len(r['products'])))
        except UnicodeEncodeError:
            log("[error] unicode error on build product request")
            exit(-1)

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

        log("[matches] found {} matching item(s)".format(len(self.matches)))

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
            ).json()
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
        except:
            log("[error] exception while getting product info json")
            exit(-1)

    def sel_product_sku(self):
        log("[prod] scanning product info for size")
        for var in self.variants:
            if var.size == self.size:
                log("[match] found a matching size {} with sku {}".format(var.size, var.sku))
                self.skupid = var.sku
                return True
        return False

    def add_to_cart(self):
        log("[atc] adding product to cart")
        if self.cart_id is None:
            log("[POST METHOD]")
            if self.site == 'JD':
                url = "https://m.jdsports.co.uk/cart/{}".format(self.skupid)
            elif self.site == 'SZ':
                url = "https://www.size.co.uk/cart/{}".format(self.skupid)
            else:
                log("[error] need to use a predefined cart ID for footpatrol")
                exit(-1)
            payload = {
                "SKU": self.skupid,
                "cartPosition": None,
                "quantityToAdd": 1,
                "customisations": []
            }
            headers = {
                "accept": "*/*",
                "origin": "https://m.jdsports.co.uk",
                "x-requested-with": "XMLHttpRequest",
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
                "content-type": "application/json",
                "dnt": "1",
                "referer": "https://m.jdsports.co.uk/product/",
                "accept-encoding": "gzip, deflate, br",
                "accept-language": "en-US,en;q=0.8",
                "cache-control": "no-cache"
            }
            r = self.s.request(
                'POST',
                url,
                headers=headers,
                data=payload
            )
            if (r.status_code >= 200) and (r.status_code < 210):
                r.json()
                log("[cart] got good status code from post request")
                self.cart_id = r['ID']
                log("[cart] cart id {}".format(self.cart_id))
            else:
                log("[error] got bad status code {} from post request".format(r.status_code))
        else:  # if we have a predefined cart ID, use it + PUT method
            log("[PUT METHOD]")
            if self.site == 'JD':
                data = '{' \
                       '"contents":[{' \
                       '"$schema":"https:\\/\\/commerce.mesh.mx\\/stores\\/jdsports\\/schema\\/CartProduct",' \
                       '"SKU":"{}",' \
                       '"quantity":1' \
                       '}]' \
                       '}'.format(self.skupid)
                r = self.s.request(
                    'PUT',
                    'https://commerce.mesh.mx/stores/jdsports/carts/' + self.cart_id,
                    headers=self.headers,
                    data=data
                )
            else:
                r = self.s.request(
                    'PUT',
                    'https://commerce.mesh.mx/stores/' + self.sitename + '/carts/' + self.cart_id + '/' + self.skupid,
                    headers=self.headers,
                    data='{"quantity":1}'
                )

            if (r.status_code >= 200) and (r.status_code < 210):
                log("[cart] got good status code from put request")
            else:
                log("[error] got bad status code {} from put request".format(r.status_code))

    def checkout(self):
        log("[checkout] check out not implemented yet")