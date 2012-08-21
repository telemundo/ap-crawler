"""
This modules crawls apexchange.com and fetches and saves all content from a stored search.

@author: Rodolfo Puig <Rodolfo.Puig@nbcuni.com>
@copyright: Telemundo Digital Media
@organization: NBCUniversal
"""

import sys, os, re, time, json, requests, yaml
from BeautifulSoup import BeautifulSoup
from optparse import OptionParser
from math import ceil

def end_exec(options, records):
    if options.verbosity >= 1 and not options.quiet:
        print '[%s] NOTICE: downloaded %d records' % (time.strftime('%Y-%m-%d %H:%M:%S'), records)
    sys.exit()

def load_config(parser, file):
    fh = open(file)
    config = yaml.load(fh)
    fh.close()
    if 'data' not in config:
        parser.error('%s is missing the "data" tree root' % file)
    if 'auth' not in config['data']:
        parser.error('%s is missing the "data/auth" subtree' % file)
    if 'search' not in config['data']:
        parser.error('%s is missing the "data/search" subtree' % file)
    return config

def mod_headers(args):
    ''' Adds the custom User-Agent to the request headers '''
    if args.get('headers') is None:
        args['headers'] = dict()
    args['headers'].update({ 'User-Agent':'apfetch/1.1 (+http://support.tlmdservices.com/)' })

    return args

def main():
    ''' Main routine '''
    parser = OptionParser(usage='usage: %prog [options] dest')
    parser.add_option("-v", action="count", dest="verbosity", default=0, help="increase output verbosity")
    parser.add_option("-q", "--quiet", action="store_true", dest="quiet", help="hide all output")
    parser.add_option("-l", "--limit", dest="records", default=25, type="int", help="number of records to fetch")
    parser.add_option("-c", "--config", dest="config", default="config.yaml", type="string", help="YAML configuration file")
    parser.add_option("-f", "--format", dest="format", default="xml", type="string", help="type of AP content to fetch")
    parser.add_option("-p", "--pause", dest="pause", default=5, type="int", help="number of seconds to wait between page fetches")
    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.error("you must specify the destination directory.")
    if not os.path.exists(options.config):
        parser.error("the configuration file %s does not exist." % options.config)
    config = load_config(parser, options.config)
    ''' Misc '''
    destination = args[0].rstrip('/')
    if not os.path.exists(destination):
        os.makedirs(destination)
    hooks = dict(args=mod_headers)
    files = []
    records = 0
    page = 0
    basedict = {
        "FilterList": "", "Entitlements": None, "Outings": None, "MatchReferences": [], "DontMatchReferences": [], "SelectedTopicID": 0, "Links": "", "Fields": "date,time,headline,slug",
        "Rows": 10, "MediaType": "Text", "UsePhotoArchive": False, "UsePressReleases": False, "UseExtendedEntitlements": False, "UseMatchRef": False, "SearchInterval": "TwoWeeks",
        "Profile": "", "WithinItems": [], "GetCounts": False, "SortBy": "arrivaldatetime:numberdecreasing", "DahStartState": None, "IsPrePublished": False, "AllowAllRelatedMedia": False,
        "IsMemberContentSearch": False, "SearchCommand": "OR", "ParentTopicID": -1, "SearchOwnerID": -1, "APQLFilterList": "", "IsMarketPlaceTopicSearch": False, "SearchType": "SavedSearch",
        "SearchItem": "", "SearchName": config['data']['search']['name'], "SearchId": config['data']['search']['id']
    }
    ''' Step 1: Create the initial session '''
    initialrequest = requests.get('http://www.apexchange.com/login.aspx', hooks=hooks);
    if options.verbosity >= 3 and not options.quiet:
        print '[%s] DEBUG: %s (%d)' % (time.strftime('%Y-%m-%d %H:%M:%S'), initialrequest.url, initialrequest.status_code)
    initialsoup = BeautifulSoup(initialrequest.content)
    initialinputs = initialsoup('input', {'type':'hidden'})
    ''' Step 2: Login to the system '''
    loginpayload = {}
    for initialinput in initialinputs:
        loginpayload[initialinput['name']] = initialinput['value']
    loginpayload['ctl00$ctl00$ctl00$ctl00$ctl00$ctl00$body$body$body_main$body_main$body_main$body_main$txtLoginName'] = config['data']['auth']['user']
    loginpayload['ctl00$ctl00$ctl00$ctl00$ctl00$ctl00$body$body$body_main$body_main$body_main$body_main$txtPassword']  = config['data']['auth']['pass']
    loginpayload['ctl00$ctl00$ctl00$ctl00$ctl00$ctl00$body$body$body_main$body_main$body_main$body_main$cbRememberMe'] = 'on'
    loginpayload['ctl00$ctl00$ctl00$ctl00$ctl00$ctl00$body$body$body_main$body_main$body_main$body_main$btnLogin']     = 'Login'
    loginrequest = requests.post('http://www.apexchange.com/login.aspx', hooks=hooks, data=loginpayload, cookies=initialrequest.cookies)
    ''' Step 3: Paginate the content '''
    pagerequest = loginrequest
    while records < options.records:
        if options.verbosity >= 1 and not options.quiet:
            print '[%s] NOTICE: fetching page %d' % (time.strftime('%Y-%m-%d %H:%M:%S'), page+1)
        pagepayload = {}
        searchdict = basedict
        if page == 0:
            searchdict['PageType'] = 'First'
            #pagepayload['jsp'] = '{"FilterList":"","Entitlements":null,"Outings":null,"MatchReferences":[],"DontMatchReferences":[],"PageType":"First","SearchItem":"","SearchId":644248,"SelectedTopicID":0,"Links":"","Fields":"date,time,headline,slug","Rows":10,"SearchType":"SavedSearch","MediaType":"Text","UsePhotoArchive":false,"UsePressReleases":false,"UseExtendedEntitlements":false,"UseMatchRef":false,"SearchInterval":"TwoWeeks","SearchName":"Olympics","Profile":"","WithinItems":[],"GetCounts":false,"SortBy":"arrivaldatetime:numberdecreasing","DahStartState":null,"IsPrePublished":false,"AllowAllRelatedMedia":false,"IsMemberContentSearch":false,"SearchCommand":"OR","ParentTopicID":-1,"SearchOwnerID":"-1","APQLFilterList":"","IsMarketPlaceTopicSearch":false}'
        else:
            searchdict['PageType'] = 'Next'
            searchdict['StartRecord'] = (page * 10) + 1
            searchdict['Page'] = page + 1
            searchdict['NextPage'] = 1
            #pagepayload['jsp'] = '{"FilterList":"","Entitlements":null,"Outings":null,"MatchReferences":[],"DontMatchReferences":[],"PageType":"Next","SearchItem":"","SearchId":644248,"SelectedTopicID":0,"Links":"","Fields":"date,time,headline,slug","Rows":10,"SearchType":"SavedSearch","MediaType":"Text","UsePhotoArchive":false,"UsePressReleases":false,"UseExtendedEntitlements":false,"UseMatchRef":false,"SearchInterval":"TwoWeeks","SearchName":"Olympics","Profile":"","WithinItems":[],"GetCounts":true,"SortBy":"arrivaldatetime:numberdecreasing","DahStartState":null,"IsPrePublished":false,"AllowAllRelatedMedia":false,"IsMemberContentSearch":false,"SearchCommand":"OR","ParentTopicID":-1,"SearchOwnerID":"-1","APQLFilterList":"","IsMarketPlaceTopicSearch":false,"StartRecord":%d,"Page":%d,"NextPage":1}' % ((page*10)+1, (page+1))
        pagepayload['jsp'] = json.dumps(searchdict)
        pagerequest = requests.get('http://www.apexchange.com/pages/portal.aspx', hooks=hooks, params=pagepayload, cookies=pagerequest.cookies)
        if options.verbosity >= 3 and not options.quiet:
            print '[%s] DEBUG: %s (%d)' % (time.strftime('%Y-%m-%d %H:%M:%S'), pagerequest.url, pagerequest.status_code)
        pagesoup = BeautifulSoup(pagerequest.content)
        pagelinks = pagesoup('a', {'onclick':re.compile('DownloadManager\.DoDownload')})
        if len(pagelinks) > 0:
            for pagelink in pagelinks:
                articlejson = re.search('\((?P<json>\{.*?\})\);', pagelink['onclick'])
                if articlejson:
                    articlepayload = json.loads(articlejson.group('json').replace("'", '"'))
                    if re.match(options.format, articlepayload['fmt'], re.IGNORECASE):
                        filename = '%s/%s.%s' % (destination, articlepayload['fid'], options.format)
                        if not os.path.exists(filename):
                            files.append(filename)
                            if options.verbosity >= 2 and not options.quiet:
                                print '[%s] INFO: fetch "%s"' % (time.strftime('%Y-%m-%d %H:%M:%S'), articlepayload['slug'])
                            ''' Step 3.1: Fetch the file information '''
                            articlepayload['Action'] = 'DoDownload'
                            articleheaders = {'content-type': 'application/json'}
                            articlerequest = requests.get('http://www.apexchange.com/pages/DownloadHandler.ashx', hooks=hooks, params=articlepayload, cookies=pagerequest.cookies, headers=articleheaders)
                            if options.verbosity >= 3 and not options.quiet:
                                print '[%s] DEBUG: %s (%d)' % (time.strftime('%Y-%m-%d %H:%M:%S'), articlerequest.url, articlerequest.status_code)
                            ''' Step 3.2: Download the requested file '''
                            downloadpayload = json.loads(articlerequest.content)
                            downloadrequest = requests.get('http://www.apexchange.com/pages/%s' % downloadpayload['ClientRefId'], hooks=hooks, cookies=pagerequest.cookies)
                            if options.verbosity >= 3 and not options.quiet:
                                print '[%s] DEBUG: %s (%d)' % (time.strftime('%Y-%m-%d %H:%M:%S'), downloadrequest.url, downloadrequest.status_code)
                            ''' Step 3.3: Store the downloaded file '''
                            fp = open(filename, 'w')
                            fp.write(downloadrequest.content)
                            fp.close()
                            if options.verbosity == 0 and not options.quiet:
                                print filename
                            records += 1
                            if records == options.records:
                                if options.verbosity >= 1 and not options.quiet:
                                    print '[%s] NOTICE: max number of records reached' % (time.strftime('%Y-%m-%d %H:%M:%S'))
                                end_exec(options, records)
                        else:
                            if filename not in files:
                                if options.verbosity >= 1 and not options.quiet:
                                    print '[%s] NOTICE: no newer records found' % (time.strftime('%Y-%m-%d %H:%M:%S'))
                                end_exec(options, records)
            if options.verbosity >= 1 and not options.quiet:
                print '[%s] NOTICE: sleeping for %d seconds' % (time.strftime('%Y-%m-%d %H:%M:%S'), options.pause)
            time.sleep(options.pause)
            page += 1
        else:
            if options.verbosity >= 1 and not options.quiet:
                print '[%s] NOTICE: no more records found' % (time.strftime('%Y-%m-%d %H:%M:%S'))
            end_exec(options, records)
    end_exec(options, records)

if __name__ == '__main__':
    main()
