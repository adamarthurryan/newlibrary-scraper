#!/usr/bin/python

from lxml import html
from lxml import etree as ElementTree

from slugify import slugify

import pprint
import html2text
import sys
import requests
import time
import os
import re
import urllib2
import multiprocessing
from itertools import chain

pp = pprint.PrettyPrinter(indent=2)

MULTI_POOL_SIZE = 32

def scrape_sources(sitemap_url):
    sitemap_page = requests.get(sitemap_url)
    tree = html.fromstring(sitemap_page.text)

    eLinks = tree.xpath('//ul[contains(concat(" ", @class, " "), "simple-sitemap-post")]//a');

    #skip the private posts for now
    eLinks = filter(lambda eLink: not eLink.text.startswith("Private"), eLinks)

    urls = map(lambda eLink: eLink.attrib['href'], eLinks)
    
    return urls


def crawl(starting_url):
    try: 
        return get_dbentry_from_link(starting_url)
    except Exception as detail:
        print "An exception occurred crawling '"+starting_url+"':", detail


def get_dbentry_from_link(link):
    db_page = requests.get(link)
    tree = html.fromstring(db_page.text)


    # header element
    eHeader = tree.xpath('//article[contains(concat(" ", @class, " "), "post")]//header[contains(concat(" ", @class, " "), "entry-header")]')[0];

    # get various header & metadata content
    main_title = eHeader.xpath('//h1[contains(concat(" ", @class, " "), "entry-title")]/text()')[0]
    eCatLinks = eHeader.xpath('//span[contains(concat(" ", @class, " "), "cat-links")]//a')
    eTagLinks = eHeader.xpath('//span[contains(concat(" ", @class, " "), "tag-links")]//a')
    eEntryDate = eHeader.xpath('//span[contains(concat(" ", @class, " "), "entry-date")]//time')[0]

    # and the main body of the content
    full_content = ""
    eContentQuery = tree.xpath('//article[contains(concat(" ", @class, " "), "post")]//div[contains(concat(" ", @class, " "), "entry-content")]')
    if len(eContentQuery)>0:

        eContent = eContentQuery[0];
        
        # convert the content part of the record to markdown, preliminary to parsing it
        full_content = html2text.html2text(ElementTree.tostring(eContent))



    # add the categories and tags to the main attributes
    cats = map(lambda eLink: eLink.text, eCatLinks)
    tags = map(lambda eLink: eLink.text, eTagLinks)
    datetime = eEntryDate.attrib['datetime']

    main_attributes = {}
    if len(cats)>0:
        main_attributes["categories"] = ", ".join(cats)
    if len(tags)>0:
        main_attributes["tags"] = ", ".join(tags)
    main_attributes["created"] = datetime
    
    
    # now we want to split the markdown by art project, each of which is introduced by a title and year 
    # see http://regexr.com/3c8jk
    title_and_year_pattern = r'^(([^,\n]*),[ ]?((\d\d\d\d([ ]?-[ ]?\d\d\d\d)?)|(\?\?\?\?)))'
    title_and_year_subst = r'---section_break---\n'

    # first use regex to find the section headings, extracting the title and year bits
    # stripping the title and year out
    # then splitting the sections into separate elements
    section_title_years_res = re.findall(title_and_year_pattern, full_content, re.M)
    section_title_years = map(lambda results: (results[1], results[3]), section_title_years_res)
    full_content = re.sub(title_and_year_pattern, title_and_year_subst, full_content, 0, re.M)
    sections = re.split(r'---section_break---', full_content)

    # for each section, extract the image urls
    # and then remove the links from the section body entirely
    image_link = r'!\[\]\(([^\)]*)\)'
    section_image_urls = map(lambda section: re.findall(image_link, section), sections)
    sections = map(lambda section: re.sub(image_link, r'', section), sections)

    # for some reason the image urls are getting newlines in the middle sometimes
    section_image_urls = map(lambda urls: map(lambda url: re.sub(r'\n', r'', url), urls), section_image_urls)


    # if the first section is non-empty, then that is the main content
    # if it is empty, well then the main content is empty
    main_content = sections[0]
    main_image_urls = section_image_urls[0]

    # now zip up all the section data and make db entries from everything
    sections.pop(0)
    section_image_urls.pop(0)
    section_zip = zip(sections, section_image_urls, section_title_years)
    
    
    # make the DBEntry instances for each section
    section_entries = map(lambda zip: DBEntry(zip[2][0], zip[1], {'year': zip[2][0]}, zip[0], []), section_zip)    

    # make and return the main DBEntry instance
    return DBEntry(main_title, main_image_urls, main_attributes, main_content, section_entries)



#some useful regexes:


class DBEntry:

    def __init__(self, title, image_urls, attributes, content, children):
        self.title = title
        self.image_urls = image_urls
        self.attributes = attributes
        self.content = content
        self.children = children


    def stats(self):
        return ("Title: " + self.title.encode('UTF-8')
            + "\nChild Count: " + str(len(self.children)) 
            + "\nAttributes: " + str(self.attributes)
            + "\nImage Count: " + str(len(self.image_urls))
            + "\nContent Length: " +str(len(self.content))
            )

    def to_markdown(self) :
        markdown = "# " + self.title.encode('UTF-8') + "\n"
        for key in self.attributes:
            markdown += "\n - " + key + ":" + self.attributes[key].encode('UTF-8')    
        markdown += "\n " + self.content.encode('UTF-8')

        return markdown


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

data_test = [
    "http://adam.newlibrary.ca/2013/07/16/a77/"
]

sources = chain(artists, ideas)

re_lastpath =  r"/([^/]+)/?$"

def get_lastpath(url) :
    matchname = re.search(re_lastpath, url)
    if (not matchname):
         raise AttributeError("Invalid source url")
    return matchname.group(1)


def print_entry(entry, parent_path, depth):
    
    
    print "#"*(depth+1) + entry.title.encode('UTF-8') 

    # print "  "*depth + entry.content #.encode('UTF-8')

    # get a name for the folder to store the images in
    name = slugify(entry.title)

    # create the image folder
    path = os.path.join(parent_path, name)

    map(lambda child_entry: print_entry(child_entry, path, depth+1), entry.children)


# write an index file for each result
def create_index(entry, parent_path):
    # get a name for the folder to save the index to
    name = slugify(entry.title)

    # create the image folder
    path = os.path.join(parent_path, name)

    # make the path if necessary
    # this should be done elsewhere?
    if not os.path.isdir(path):
        os.makedirs(path)

    # create the index text
    index = entry.to_markdown()

    filepath = os.path.join(path, "index.md")

    # write the file
    with open(filepath, "w") as text_file:
        text_file.write(index)

    map(lambda child_entry: create_index(child_entry, path), entry.children)




# return a list of tuples containing the image path
def process_image_downloads(entry, parent_path):

    # get a name for the folder to store the images in
    name = slugify(entry.title)

    # create the image folder
    path = os.path.join(parent_path, name)

    # make the path if necessary
    # this should be done elsewhere
    if not os.path.isdir(path):
        os.makedirs(path)
    
    # extract the image name for each image url
    image_names = map(get_lastpath, entry.image_urls)
    paths = [path] * len(entry.image_urls)

    # the results are a list of (path, image_name, image_url) tuples
    main_results = zip (paths, image_names, entry.image_urls)

    child_results_2d = map (lambda child_entry: process_image_downloads(child_entry, path), entry.children)
    child_results = reduce (chain, child_results_2d, [])

    return chain(main_results, child_results)


def do_image_download(image_download):
    (path, image_name, image_url) = image_download

    target_path = os.path.join(path, image_name)
    
    image=urllib2.urlopen(image_url)
    open(target_path,"wb").write(image.read())

    print image_url
    print "   ", "=>", path
    print


enable_image_download = True
results_dir = "results"

def process_args():
    global enable_image_download

    for arg in sys.argv[1:]:

        # flags
        # Since flags are processed along with the video files (instead of as a separate loop), flags will only take effect for subsequent files.
        if arg == "--no-image-download" or arg == "-n":
            enable_image_download = False

        elif arg == "--help" or arg == "-?":
            print "Usage: scrape.py [OPTION]... "
            print "Scrape newlibrary site into local filesystem."
            print ""
            print "Options:"
            print "  --no-image-download, "
            print "   -n                     do not download images"
            print "  -?, --help              display this message"
            print ""
            print "Example:"
            print "  scrape.py"
            return


# the following section should only run in the first process
# this is required for multiprocessing on Windows
if __name__ == '__main__':

    sources = scrape_sources("http://adam.newlibrary.ca/sitemap/")

    process_args()

    # allocate a pool of workers to do the scraping
    multi_pool = multiprocessing.Pool(MULTI_POOL_SIZE)

    pp.pprint(sources)

    # scrape a list of entries for each source
    # store in a list of (source, entry) tuples
    entries = multi_pool.map(crawl, sources)

    # remove any entries that failed to load
    entries = filter(lambda entry: entry != None, entries)

    # print a summary of the results
    map(lambda entry: print_entry(entry, results_dir, 0), entries)

    # create the index.md files for each result
    map(lambda entry: create_index(entry, results_dir), entries)

    # create a list of all image downloads with their locations
    image_downloads_2d = map(lambda entry: process_image_downloads(entry, results_dir), entries)
### test this!
    image_downloads_all = reduce(chain, image_downloads_2d)

    # and do the downloading - multithreaded
    if enable_image_download:
        multi_pool.map(do_image_download, image_downloads_all)
