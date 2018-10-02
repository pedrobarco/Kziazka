#!/usr/bin/python

import pprint
import sys, os
import re
import configparser
from pathlib import Path
from apiclient.discovery import build
from PyPDF2 import PdfFileReader, PdfFileWriter
from colorama import init, Fore, Style


def search_book_by_title(title):
    """ Get books by title.
    The books API has a volumes().list() method that is used to list books
    given search criteria. Arguments provided are:
    volumes source ('public')
    The method returns an apiclient.http.HttpRequest object that encapsulates
    all information needed to make the request, but it does not call the API.
    The execute() function on the HttpRequest object actually calls the API.
    It returns a Python object built from the JSON response. You can print this
    object or refer to the Books API documentation to determine its structure.
    Accessing the response like a dict object with an 'items' key returns a list
    of item objects (books). The item object is a dict object with a 'volumeInfo'
    key. The volumeInfo object is a dict with keys 'title' and 'authors'.
    """
    request = service.volumes().list(q=title, maxResults=max_results)
    response = request.execute()

    books = response.get('items', [])

    return books

def search_book_by_isbn(isbn):
    request = service.volumes().list(q=f'isbn:{isbn}', maxResults=max_results)
    response = request.execute()

    books = response.get('items', [])

    return books

def get_book_by_id(bid):
    """ Get book by id.
    Google books API uses volumeId to get a specific
    book.
    """
    request = service.volumes().get(volumeId=bid)
    response = request.execute()
    return response

def list_files():
    """ List all files.
    Checks if there is any books to tag and sort.
    """
    items = []
    items = [os.path.join(dp, f) for dp, dn, filenames in os.walk(input_path) for f in filenames if f.endswith(file_ext)]
    print(f'{input_path} ({len(items)} items)')
    [file_menu(f) for f in items]

def file_menu(f):
    print(f'{Fore.GREEN}[Found]{Fore.RESET} {os.path.split(f)[1]}')
    print(tag_options)
    option = input().lower()
    if option == 'i':
        tag_by_isbn(f)
    elif option == 't':
        tag_by_title(f)
    elif option == 's':
        pass
    elif option == 'b':
        sys.exit(0)
    else:
        auto_tag(f)

def auto_tag(f):
    file = clean_non_alphanum(os.path.split(f)[1])
    books = search_book_by_title(file)
    try: 
        bid = books[0]['id']
        book = get_book_by_id(bid)
        tag(f, book)
    except:
        print(f'{Fore.RED}[ERROR]{Fore.RESET} Book search: No results found.')
        file_menu(f)

def tag_by_isbn(f):
    isbn = input('ISBN: ')
    books = search_book_by_isbn(isbn)
    try: 
        bid = books[0]['id']
        book = get_book_by_id(bid)
        tag(f, book)
    except:
        print(f'{Fore.RED}[ERROR]{Fore.RESET} Book search: No results found.')
        file_menu(f)
    bid = books[0]['id']
    book = get_book_by_id(bid)
    tag(f, book)

def tag_by_title(f):
    title = input('Title: ')
    books = search_book_by_title(title)
    print_book_search_results(books)
    print(tag_by_title_options)
    option = input().lower()
    index = eval(option) - 1 if option.isnumeric() else 0
    if option == 'b':
        file_menu(f)
    elif option == 'r':
        tag_by_title(f)
    else:
        if index >= 0 and index < len(books):
            bid = books[index]['id']
        else:
            bid = books[0]['id']
        book = get_book_by_id(bid)
        tag(f, book)

def tag(f, book):
    fin = open(f, 'rb')
    reader = PdfFileReader(fin, strict=False)
    writer = PdfFileWriter()
    writer.appendPagesFromReader(reader)

    volume = book['volumeInfo']
    authors = volume['authors']
    authors_m = ', '.join(authors) if 'authors' in volume else 'Unknown'
    title = volume['title']
    subtitle = volume['subtitle'] if 'subtitle' in volume else None
    category = volume['categories'][0].split(' / ')[0] if 'categories' in volume else 'Unsorted'
    publisher = volume['publisher'].replace('"', '') if 'publisher' in volume else None
    published_date = volume['publishedDate'] if 'publishedDate' in volume else None
    description = clean_html(volume['description']) if 'description' in volume else None
    url = volume['previewLink']
    for idd in volume['industryIdentifiers']:
        if idd['type'] == file_isbn:
            isbn = idd['identifier']

    metadata = gen_metadata(authors_m, title, subtitle, category, publisher, published_date, description, isbn)
    writer.addMetadata(metadata)

    new_filename = gen_filename(category, authors, title, isbn)
    directory = os.path.split(new_filename)[0]
    old_filename = f.replace('\\', '/')

    print_tagging_progress(old_filename, new_filename, url)

    print(apply_options)
    option = input().lower()
    if option == 's':
        pass
    else:
        if not os.path.exists(directory):
            os.makedirs(directory)
        fout = open(new_filename, 'wb')
        writer.write(fout)
        fin.close()
        fout.close()
        os.remove(f)


def gen_metadata(authors, title, subtitle, category, publisher, published_date, description, isbn):
    metadata = {
        '/Author': authors,
        '/Title': title,
        '/Category': category,
        '/ISBN': isbn
    }
    if subtitle is not None: metadata['/Subtitle'] = subtitle
    if publisher is not None: metadata['/Publisher'] = publisher
    if published_date is not None: metadata['/PublisherDate'] = published_date
    if description is not None: metadata['/Description'] = description
    return metadata

def gen_filename(category, authors, title, isbn):
    authors_f = ' & '.join(authors)
    directory = f'{output_path}/{category}/{title} [{isbn}]'
    filename = f'{directory}/{title} - {authors_f}{file_ext}'
    return filename

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    clean_text = re.sub(cleanr, '', raw_html)
    return clean_text

def clean_non_alphanum(filename):
    cleanr1 = re.compile(r'\([^)]*\)')
    cleanr2 = re.compile(r'[\W_]+')
    clean_filename = re.sub(cleanr1, '', filename)
    clean_filename = re.sub(cleanr2, ' ', clean_filename)
    return clean_filename
    
def print_book_search_results(books):
    if not books:
        print(f'{Fore.RED}[ERROR]{Fore.RESET} Book search: No results found.')
    else:
        print(f'{Fore.GREEN}[Found]{Fore.RESET} {len(books)} books')
        i = 1
        for book in books:
            b = book['volumeInfo']
            print('(%d) Title: %s, Authors: %s' % (
            i,
            b['title'],
            b['authors'] if 'authors' in b else ['Unkown']))
            i += 1

def print_tagging_progress(old_filename, new_filename, url):
    print(f'{Fore.YELLOW}[Tagging]{Fore.RESET}')
    print(f'{Fore.RED}<- {Fore.RESET}{old_filename}')
    print(f'{Fore.GREEN}-> {Fore.RESET}{new_filename}')
    print(f'{Fore.GREEN}[URL] {Fore.RESET}{url}')

tag_by_title_options = f'{Fore.BLUE}[1]{Fore.RESET}th, \
{Fore.BLUE}B{Fore.RESET}ack, \
{Fore.BLUE}R{Fore.RESET}eset ?'

tag_options = f'{Fore.BLUE}[A]{Fore.RESET}uto, \
By {Fore.BLUE}I{Fore.RESET}SBN, \
By {Fore.BLUE}T{Fore.RESET}itle, \
{Fore.BLUE}S{Fore.RESET}kip, \
a{Fore.BLUE}B{Fore.RESET}ort ?'

apply_options = f'{Fore.BLUE}[A]{Fore.RESET}pply, \
{Fore.BLUE}S{Fore.RESET}kip ?'

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('config.ini')

    api_key = config['DEV']['API_KEY']
    input_path = config['USER']['INPUT_PATH']
    output_path = config['USER']['OUTPUT_PATH'] + 'Books'
    file_ext = config['DEFAULT']['FILE_EXT']
    file_isbn = config['DEFAULT']['FILE_ISBN']
    max_results = config['DEFAULT']['MAX_RESULTS']

    init(autoreset=True)
    # The apiclient.discovery.build() function returns an instance of an API service
    # object that can be used to make API calls. The object is constructed with
    # methods specific to the books API. The arguments provided are:
    #   name of the API ('books')
    #   version of the API you are using ('v1')
    #   API key
    service = build('books', 'v1', developerKey=api_key)

    list_files()
