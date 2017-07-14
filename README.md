## Mesh Bot

Python script to scrape products from one of 3 Mesh Commerce platforms. If a scraped product matches the configured 
keywords, the script adds the product to cart. Designed for shoe releases.

## Config

Change the settings in config.json to match your needs. Positive keyword search is greedy, meaning products must match
all keywords. Separate with comas. See config.example.json for more formatting help.

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

## Known Issues

You need a predefined cart ID for Footpatrol. Havent found a way around this yet. You can scrape Cart ID using Charles
Proxy or something similar to sniff mobile traffic. 

## Todo

* Proxy support with multithreading
* Full checkout
* Add support for Footpatrol missing cart ID


## License

Released under MIT license. Credit is nice.