#!/usr/bin/python

from lxml import html
import requests
import time
import os
import re
import urllib
import multiprocessing

MULTI_POOL_SIZE = 8

def crawl(starting_url):
    return get_dbentry_from_link(starting_url)

def get_dbentry_from_link(link):
    db_page = requests.get(link)
    tree = html.fromstring(db_page.text)

    # header element
    eHeader = tree.xpath('//article[contains(concat(" ", @class, " "), "post")]//header[contains(concat(" ", @class, " "), "entry-header")]')[0];

#    eHeader = tree.xpath('//article//header[@class="entry-header"]')[0];

    # get various header & metadata content
    title = eHeader.xpath('//h1[contains(concat(" ", @class, " "), "entry-title")]/text()')[0]
    eCatLinks = eHeader.xpath('//span[contains(concat(" ", @class, " "), "cat-links")]//a')
    eTagLinks = eHeader.xpath('//span[contains(concat(" ", @class, " "), "tags-links")]//a')
    eEntryDate = eHeader.xpath('//span[contains(concat(" ", @class, " "), "entry-date")]//time')[0]

    # ignore author, 'cause it's me

    eContent = tree.xpath('//article[contains(concat(" ", @class, " "), "post")]//div[contains(concat(" ", @class, " "), "entry-content")]')[0];

    imageUrls = eContent.xpath('//img/@src');
    

    dbEntry = DBEntry(title, imageUrls)

    return dbEntry


class DBEntry:

    def __init__(self, title, image_urls):
        self.title = title
        self.image_urls = image_urls

    def __str__(self):
        return ("Title: " + self.title.encode('UTF-8') + 
        "\nNum Images: " + str(len(self.image_urls)))


artists = [
    # social architecture
    "http://adam.newlibrary.ca/2014/05/09/gregory-kloehn/",
    "http://adam.newlibrary.ca/2014/05/04/the-heidelberg-project/",

    # design & art architecture
    "http://adam.newlibrary.ca/2014/05/01/boneyard-studios/",
    "http://adam.newlibrary.ca/2014/04/29/queens-walk-window-gardens/",
    "http://adam.newlibrary.ca/2014/04/25/fabian-marti/",
    "http://adam.newlibrary.ca/2014/04/16/bookmobile/",
    "http://adam.newlibrary.ca/2014/02/18/katie-bethune-leaman/",
    "http://adam.newlibrary.ca/2014/02/18/penique-productions/",
    "http://adam.newlibrary.ca/2014/01/25/n55/",
    "http://adam.newlibrary.ca/2014/01/22/steve-topping/",
    "http://adam.newlibrary.ca/2014/01/26/kathy-prendergast/",
    "http://adam.newlibrary.ca/2013/11/20/wild-pansy-press/",
    "http://adam.newlibrary.ca/2013/08/20/tadashi-kawamata/",
    "http://adam.newlibrary.ca/2013/07/24/andrea-zittle/",
    "http://adam.newlibrary.ca/2013/07/16/a77/",
    "http://adam.newlibrary.ca/2013/07/09/ffb-oslo/",
    "http://adam.newlibrary.ca/2013/07/07/re-do-studio/",
    "http://adam.newlibrary.ca/2013/05/29/kim-adams/",
    "http://adam.newlibrary.ca/2013/06/22/van-bo-le-menzel/",
    "http://adam.newlibrary.ca/2013/03/07/werner-schroedl/",
    "http://adam.newlibrary.ca/2013/02/07/filip-dujardin/",
    "http://adam.newlibrary.ca/2012/10/27/michael-rakowitz/",
    "http://adam.newlibrary.ca/2012/09/27/gordon-matta-clark/",

    # modern architecture
    "http://adam.newlibrary.ca/2014/02/15/archigram/",

    # social practice
    "http://adam.newlibrary.ca/2014/05/16/yyz-lending-library/",
    "http://adam.newlibrary.ca/2014/05/04/theaster-gates/",
    "http://adam.newlibrary.ca/2014/04/18/the-silent-university/",
    "http://adam.newlibrary.ca/2014/03/14/tom-marioni/",
    "http://adam.newlibrary.ca/2014/03/09/jp-king/",
    "http://adam.newlibrary.ca/2014/01/23/atsa-laction-terroriste-socialement-acceptable/",

    # design
    "http://adam.newlibrary.ca/2014/08/11/foldschool/",
    "http://adam.newlibrary.ca/2014/02/18/michel-de-broin/",
    "http://adam.newlibrary.ca/2014/02/03/tejo-remy/"
]

ideas = [
"http://adam.newlibrary.ca/2014/04/29/allotment-shed/",
"http://adam.newlibrary.ca/2014/04/23/a-cabin-in-a-loft/",
"http://adam.newlibrary.ca/2014/04/23/tree-pod/",
"http://adam.newlibrary.ca/2014/02/23/little-free-library/",
"http://adam.newlibrary.ca/2014/03/09/fogo-island-residency/"
]

sources = ideas

re_lastpath =  r"/([^/]+)/?$"

def get_lastpath(url) :
    matchname = re.search(re_lastpath, url)
    if (not matchname):
         raise AttributeError("Invalid source url")
    return matchname.group(1)


def print_result(result):
    (source, entry) = result

    print "# Processing Entry"
    print "URL:", source
    print entry

    # get a name for the folder to store the images in
    name = get_lastpath(source)

    # create the image folder
    path = os.path.join("images", name)

    print "Images Path:", path
    print



# return a list of tuples containing the image path
def process_image_downloads(result):
    (source, entry) = result

    # get a name for the folder to store the images in
    name = get_lastpath(source)

    # create the image folder
    path = os.path.join("images", name)

    # make the path if necessary
    # this should be done elsewhere
    if not os.path.isdir(path):
        os.makedirs(path)

    # extract the image name for each image url
    image_names = map(get_lastpath, entry.image_urls)
    paths = [path] * len(entry.image_urls)

    # return a list of (path, image_name, image_url) tuples
    return zip (paths, image_names, entry.image_urls)


def do_image_download(image_download):
    (path, image_name, image_url) = image_download

    target_path = os.path.join(path, image_name)

    urllib.urlretrieve (image_url, target_path)

    print image_url
    print "   ", "=>", path
    print

# the following section should only run in the first process
# this is required for multiprocessing on Windows
if __name__ == '__main__':

    # allocate a pool of workers to do the scraping
    multi_pool = multiprocessing.Pool(MULTI_POOL_SIZE)

    # scrape an entry for each source
    # store in a list of (source, entry) tuples
    entries = multi_pool.map(crawl, sources)
    results = zip (sources, entries)

    # print a summary of the results
    map(print_result, results)

    # create a list of all image downloads with their locations
    image_downloads_all = []
    image_downloads_2d = map(process_image_downloads, results)
    for image_downloads in image_downloads_2d:
        image_downloads_all.extend(image_downloads)

    multi_pool.map(do_image_download, image_downloads_all)

    # process the results, downloading the images as appropriate
    #multi_pool.map(process_result, results)