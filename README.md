## Mesh Bot

Python script to scrape products from one of 3 Mesh Commerce platforms. If a scraped product matches the configured 
keywords, the script adds the product to cart and checks out. Designed for shoes releases so be careful if you try and bot clothing. Dont know how the size matcing will work out.

These orders are likely to get canceled.

## Config

Change the settings in config.json to match your needs. Positive keyword search is greedy, meaning products must match
all keywords. Separate with comas. See config.example.json for more formatting help.

Blank values must be set to null. 

Each config file (excluding config.example.json) in the 'configs' folder represents a separate task. 


## Usage

#### Installation

```
$ cd Mesh
$ pip install -r requirements.txt
```

#### Running

```
$ python main.py
```

#### Modes

There are three main modes for this bot. One is to scrape the site pages for matching products (this is pretty obselete considering it wont scrape backend).

The other modes require a PID or a PID.SKU to be predefined (this will come from a scraper...s/o crep).

## Known Issues

~~Have had trouble posting to DataCash card endpoint. Workin on it.~~

## Todo

* Make this less of a PEP8 nightmare
* Proxy support with ~~multithreading~~
* ~~Full checkout~~
* ~~Add support for Footpatrol missing cart ID~~


## License

Released under MIT license. Credit is nice.