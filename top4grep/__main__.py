import argparse
import re
from itertools import zip_longest

import sqlalchemy
from nltk import download, word_tokenize
from nltk.data import find
from nltk.stem import PorterStemmer

from . import DB_PATH, Session
from .db import Paper
from .utils import new_logger

logger = new_logger("Top4Grep")
stemmer = PorterStemmer()

CONFERENCES = ["RAID", "ESORICS", "ACSAC", "AsiaCCS", "PETS", "WWW", "IEEE EuroS&P", "NDSS", "IEEE S&P", "USENIX", "CCS"]

# Function to check and download 'punkt' if not already available
def check_and_download_punkt():
    try:
        # Check if 'punkt' is available, this will raise a LookupError if not found
        find('tokenizers/punkt')
        #print("'punkt' tokenizer models are already installed.")
    except LookupError:
        print("'punkt' tokenizer models not found. Downloading...")
        # Download 'punkt' tokenizer models
        download('punkt')
        download('punkt_tab')
        
# trim word tokens from tokenizer to stem i.e. exploiting to exploit
def fuzzy_match(title):
    tokens = word_tokenize(title)
    return [stemmer.stem(token) for token in tokens]
    
def existed_in_tokens(tokens, keywords):
    return all(map(lambda k: stemmer.stem(k.lower()) in tokens, keywords))

def grep(keywords, abstract):
    # TODO: currently we only grep either from title or from abstract, also grep from other fields in the future maybe?
    if abstract:
        constraints = [Paper.abstract.contains(x) for x in keywords]
        with Session() as session:
            papers = session.query(Paper).filter(*constraints).all()
        filter_paper = filter(lambda p: existed_in_tokens(fuzzy_match(p.abstract.lower()), keywords), papers)
    else:
        constraints = [Paper.title.contains(x) for x in keywords]
        with Session() as session:
            papers = session.query(Paper).filter(*constraints).all()
        #check whether whether nltk tokenizer data is downloaded
        check_and_download_punkt()
        #tokenize the title and filter out the substring matches
        filter_paper = []
        for paper in papers:
            if all([stemmer.stem(x.lower()) in fuzzy_match(paper.title.lower()) for x in keywords]):
                filter_paper.append(paper)
    # perform customized sorthing
    papers = sorted(filter_paper, key=lambda paper: paper.year + CONFERENCES.index(paper.conference)/10, reverse=True)
    return papers

def grep_regexp(regexps, abstracts):
    logger.info(regexps)
    if abstracts:
        constraints = [sqlalchemy.or_(Paper.title.op('REGEXP')(regexp), Paper.abstract.op('REGEXP')(regexp)) for regexp in regexps]
    else:
        constraints = [Paper.title.op('REGEXP')(regexp) for regexp in regexps]
    with Session() as session:
        papers = session.query(Paper).filter(*constraints).all()
    papers = sorted(papers, key=lambda paper: paper.year + CONFERENCES.index(paper.conference)/10, reverse=True)
    return papers

COLORS = [
    "\033[91m", # red
    "\033[92m", # green
    "\033[93m", # yellow
    "\033[94m", # light purple
    "\033[95m", # purple
    "\033[96m" # cyan
]

def show_papers(papers, keywords, show_abstracts=False):
    longest_conf = max([len(paper.conference) for paper in papers], default=0)
    for paper in papers:
        abstract = paper.abstract
        title = paper.title
        for (k,c) in zip_longest(keywords, COLORS, fillvalue="\033[96m"):
            kre = re.compile("(" + re.escape(k) + ")", re.IGNORECASE)
            abstract = kre.sub(c + "\\1" "\033[00m", abstract)
            title = kre.sub(c + "\\1" + "\033[00m", title)
        if paper.url:
            ansi_link = f"\033]8;;{paper.url}\033\\{title}\033]8;;\033\\"
        else:
            ansi_link = title
        header = f"{paper.year}: {paper.conference:{longest_conf}s} - {ansi_link}"
        print(header)
        if show_abstracts and abstract:
            print(abstract.strip())
            print("")

def show_papers_regexp(papers, regexps, show_abstracts=False):
    longest_conf = max([len(paper.conference) for paper in papers], default=0)
    for paper in papers:
        abstract = paper.abstract
        title = paper.title
        for regexp in regexps:
            offset = 0
            for re_match in re.finditer(regexp, title):
                if paper.url:
                    start = re_match.start(0) + offset
                    end = re_match.end(0) + offset
                    offset += len("\033[1;31m")
                    offset += len("\033[1;34m")
                    title = title[:start] + "\033[1;31m" + title[start:end] + "\033[1;34m" + title[end:]
                else:
                    start = re_match.start(0) + offset
                    end = re_match.end(0) + offset
                    offset += len("\033[1;31m")
                    offset += len("\033[0m")
                    title = title[:start] + "\033[1;31m" + title[start:end] + "\033[0m" + title[end:]
            offset = 0
            for re_match in re.finditer(regexp, abstract):
                start = re_match.start(0) + offset
                end = re_match.end(0) + offset
                offset += len("\033[1;31m")
                offset += len("\033[0m")
                abstract = abstract[:start] + "\033[1;31m" + abstract[start:end] + "\033[0m" + abstract[end:]
        if paper.url:
            ansi_link = f"\033[1;34m\033]8;;{paper.url}\a{title}\033]8;;\033[0m"
        header = f"{paper.year}: {paper.conference:{longest_conf}s} - {ansi_link}"
        print(header)
        if show_abstracts and abstract:
            print(abstract.strip())
            print("")

def list_missing_abstract():
    with Session() as session:
        papers = session.query(Paper).filter(Paper.abstract == "").all()
    for paper in papers:
        print(paper)

def main():
    parser = argparse.ArgumentParser(description='Scripts to query the paper database',
                                     usage="%(prog)s [options] -k <keywords>")
    parser.add_argument('-r', type=str, help="keywords to regexp multiple (and concatenated) regexp separated by #. For example, 'linux|kernel|exploit#android|CVE'", default='^$')
    parser.add_argument('--build-db', action="store_true", help="Builds the database of conference papers")
    parser.add_argument('--missing-abstract', action="store_true", help="List the papers that do not have abstracts")
    parser.add_argument('--abstracts', action="store_true", help="Involve abstract into the database's building or query (Need Chrome for building)")
    args = parser.parse_args()

    if args.missing_abstract and not args.build_db:
        list_missing_abstract()
        return
    
    if args.r:
        regexps = args.r.split("#")
        assert DB_PATH.exists(), "need to build a paper database first to perform wanted queries"
        regexp = args.r
        papers = grep_regexp(regexps,args.abstracts)
        show_papers_regexp(papers,regexps,args.abstracts)
        logger.debug(f"Found {len(papers)} papers")
    elif args.build_db:
        print("Building db...")
        try:
            from .build_db import build_db
        except ModuleNotFoundError:
            logger.error("Failed to import build_db. Please make sure you have the required dependencies installed. Try running 'pip install .[BUILD]'")
            return
        build_db(args.abstracts, args.missing_abstract)


if __name__ == "__main__":
    main()
