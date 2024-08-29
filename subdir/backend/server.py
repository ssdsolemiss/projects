import configparser
from datetime import datetime
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS, cross_origin
import requests
from collections import namedtuple
# import os



Document = namedtuple('Document', ['eid', 'doi', 'pii', 'pubmed_id', 'title', 'subtype', 'subtypeDescription',
                                   'creator', 'afid', 'affilname', 'affiliation_city', 'affiliation_country',
                                   'author_count', 'author_names', 'coverDate',
                                   'coverDisplayDate', 'publicationName', 'issn', 'source_id', 'eIssn',
                                   'aggregationType', 'volume', 'issueIdentifier', 'article_number', 'pageRange',
                                   'description', 'authkeywords', 'citedby_count', 'openaccess', 'freetoread',
                                   'freetoreadLabel', 'fund_acr', 'fund_no', 'fund_sponsor', 'url'])

quarters_dict = {
    'quarter_1': ['January', 'February', 'March'],
    'quarter_2': ['April', 'May', 'June'],
    'quarter_3': ['July', 'August', 'September'],
    'quarter_4': ['October', 'November', 'December'],
}

def read_api_keys():
    config = configparser.ConfigParser()
    config.read('config.cfg')
    api_keys = config.get('API_KEYS', 'keys')
    return api_keys

api_keys = read_api_keys()


# Initialize Flask app
app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": "http://localhost:8080"}})
app.config['CORS_HEADERS'] = 'Content-Type'

@app.before_request
def before_request():
    if request.method == 'OPTIONS':
        return build_cors_preflight_response()

def build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "http://localhost:8080")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    return response

# Route to handle data submission
@app.route('/scopus/data', methods=['POST'])
# @cross_origin(origin='localhost', headers=['Content-Type', 'Authorization'])
def getData():
    api_keys = read_api_keys()
    data = request.json
    pubYear = data.get('publicationYear')
    searchType = 'annual' if data.get('searchType') == 'a' else 'quarter'
    quarter = data.get('quarterNumber') if 'quarterNumber' in data else None

    print(f"Publication Year: {pubYear}, Search Type: {searchType}, Quarter: {quarter}")
    filename = execute_scopus_api(pubYear, searchType, quarter, api_keys)

    if filename != 'nothing':
        response_data = {
            'message': 'Data received successfully',
            'filename': filename,
        }
        return jsonify(response_data), 200
    else:
        return jsonify({'message': 'Failed to generate data. Check parameters.'}), 400

def getAbstractRetrieval(doi, api_key):
    base_url = 'https://api.elsevier.com/content/abstract/doi/'
    url = f"{base_url}{doi}"

    headers = {
        'Accept': 'application/json',
        'X-ELS-APIKey': api_key  # Use the correct API key format
    }

    try:
        row = []
        author_list = []
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the JSON response
        data = response.json()

        # Extracting core data and authors from JSON
        coredata = data.get('abstracts-retrieval-response', {}).get('coredata', {})
        authors = data.get('abstracts-retrieval-response', {}).get('authors', {}).get('author', [])

        # Extract metadata
        title = coredata.get('dc:title', ' ')
        journal = coredata.get('prism:publicationName', ' ')
        volume = coredata.get('prism:volume', ' ')
        issue = coredata.get('prism:issueIdentifier', ' ')
        publication_date = coredata.get('prism:coverDate', 'No Publication Date')
        ab_doi = coredata.get('prism:doi', ' ')
        start_page = 'None'
        if coredata.get('prism:pageRang'):
            start_page = coredata.get('prism:pageRange')
        # ab_url = next((link.get('@href', 'No URL') for link in coredata.get('link', []) if link.get('@rel') == 'scopus'), 'No URL')
        row += [title, journal, volume, issue, publication_date, ab_doi, start_page]
        # Format authors in RIS format
        author_list = "\n".join([f"AU  - {author.get('ce:surname', '')} {author.get('ce:indexed-name', '').split()[1] if 'ce:indexed-name' in author and len(author.get('ce:indexed-name', '').split()) > 1 else ''}" for author in authors])


        # Prepare RIS format
        ris_format = [
            "TY  - JOUR",
            f"TI  - {title}",
            f"JO  - {journal}",
            f"VL  - {volume}",
            f"DA  - {publication_date}",
            f"PY  - {publication_date[:4]}",
            f"SP  - {start_page}",
            author_list,
            f"DO  - {ab_doi}",
            f"UR  - https://doi.org/{ab_doi}",
            f"IS  - {issue}",
            
            "ER  - "
        ]
        
        string = '\n'.join(ris_format)
        string += '\n'

        return string

    except requests.exceptions.RequestException as e:
        print(f"HTTP error occurred: {e}")
        return None
    except Exception as e:
        print(f"Error occurred (in abstract retrieval function): {e}")
        print(row)
        print(authors)
        return None

def getAuths(url, api_keys):
    base_url = url
    headers = {
        'Accept': 'application/json',
        'X-ELS-APIKey': api_keys
    }

    try:
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()  # Raise error for bad response status

        data = response.json()
        authors_list = []

        # Handling different structures of author information
        authors_response = data.get("abstracts-retrieval-response", {}).get('authors')
        if authors_response:
            if 'author' in authors_response:
                authors = authors_response["author"]
                for author in authors:
                    surname = author["preferred-name"]["ce:surname"]
                    given_name = author["preferred-name"].get("ce:given-name", "")
                    full_name = f"{surname}, {given_name}" if given_name else surname
                    authors_list.append(full_name)
            elif 'author-group' in authors_response:
                author_group = authors_response["author-group"]
                if isinstance(author_group, list):
                    for group in author_group:
                        authors = group.get("author", [])
                        for author in authors:
                            surname = author["preferred-name"]["ce:surname"]
                            given_name = author["preferred-name"].get("ce:given-name", "")
                            full_name = f"{surname}, {given_name}" if given_name else surname
                            authors_list.append(full_name)
                elif isinstance(author_group, dict):
                    authors = author_group.get("author", [])
                    for author in authors:
                        surname = author["preferred-name"]["ce:surname"]
                        given_name = author["preferred-name"].get("ce:given-name", "")
                        full_name = f"{surname}, {given_name}" if given_name else surname
                        authors_list.append(full_name)

        return authors_list if len(authors_list) else []

    except requests.exceptions.RequestException as e:
        print(f"Error fetching authors: {e}")
        return []
    except Exception as e:
        print(f"in author An unexpected error occurred: {e}")
        return []



def execute_scopus_api(pubYear, searchType, quarter, api_keys, count = 25):
    
    api = api_keys
    pubMonths = quarters_dict.get(quarter, [])

    start_time = datetime.now().replace(microsecond=0)
    base_url = 'https://api.elsevier.com/content/search/scopus'
    
    if searchType == 'annual':
        search_query = f'(((AF-ID (60010491) AND (pharmacy OR "biomolecular sciences" OR "natural products research" OR pharmaceutics)) OR AF-ID (60020462) OR AF-ID (60030187)) AND PUBYEAR = {pubYear})'
        
    elif searchType == 'quarter' and pubMonths:
        search_query = f'(((AF-ID (60010491) AND (pharmacy OR "biomolecular sciences" OR "natural products research" OR pharmaceutics)) OR AF-ID (60020462) OR AF-ID (60030187)) AND PUBDATETXT ( "{pubMonths[0]} {pubYear}" OR "{pubMonths[1]} {pubYear}" OR "{pubMonths[2]} {pubYear}" ) AND PUBYEAR = {pubYear})'
        
    else:
        return 'nothing'  # Handle invalid searchType or quarter

    base_url = 'https://api.elsevier.com/content/search/scopus'
    headers = {
        'Accept': 'application/json',
        'X-ELS-APIKey': api
    }
    params = {
        'query': search_query,
        'start': 0,
        'count': count
    }
    filename = f'UM_Pharmacy_Publications_{pubYear}.ris' if searchType == 'annual' else f'UM_Pharmacy_Publications_{pubMonths[0]}_to_{pubMonths[2]}_{pubYear}.ris'
    total_results = []
    documents = []
    start_time = datetime.now().replace(microsecond=0)
    try:
        with open(filename, 'w', encoding='utf-8') as outfile:

            counting = 0
            exception_count = 0
            exceptions_list = []

            while True:
                try:
                    response = requests.get(base_url, headers=headers, params=params)
                    response.raise_for_status()  # Raise error for bad response status

                    data = response.json()
                    entries = data.get('search-results', {}).get('entry', [])
                    total_results.extend(entries)

                    # Check if there are more results
                    if len(entries) < count:
                        break
                    
                    # Increment start for the next page
                    params['start'] += count

                    # Implement rate limiting
                    # time.sleep(1)  # Example: Sleep for 1 second between requests
                        
                except requests.exceptions.HTTPError as http_err:
                    print(f"HTTP error occurred: {http_err}")
                    break
                except Exception as e:
                    print(f"Error fetching results: {e}")
                    break

            print(len(total_results))  # Print total number of entries fetched
            # print(total_results[0])


            for entry in total_results:
                # Extract affiliations
                affiliations = entry.get('affiliation', [])
                if isinstance(affiliations, list) and affiliations:
                    affiliation = affiliations[0]
                    afid = affiliation.get('afid')
                    affilname = affiliation.get('affilname')
                    affiliation_city = affiliation.get('affiliation-city')
                    affiliation_country = affiliation.get('affiliation-country')
                else:
                    afid = 'None'
                    affilname = 'None'
                    affiliation_city = 'None'
                    affiliation_country = 'None'
                
                # Extract authors
                

                #new method of retrieving authors
                url_list = entry.get('link', [])
                if url_list:
                    url = url_list[1].get("@href")
                    author_list = getAuths(url, api_keys)
                else:
                    author_list = []
                


                # Extract freetoread and freetoreadLabel
                freetoread = entry.get('freetoread', [])
                if isinstance(freetoread, dict):
                    freetoread = freetoread.get('value', [])
                freetoreadLabel = entry.get('freetoreadLabel', [])
                if isinstance(freetoreadLabel, dict):
                    freetoreadLabel = freetoreadLabel.get('value', [])

                # Create Document object
                doc = Document(
                    eid=entry.get('eid', ''),
                    doi=entry.get('prism:doi', None),
                    pii=entry.get('pii', ''),
                    pubmed_id=entry.get('pubmed-id', ''),
                    title=entry.get('dc:title', ''),
                    subtype=entry.get('subtype', ''),
                    subtypeDescription=entry.get('subtypeDescription', ''),
                    creator=entry.get('dc:creator', ''),
                    afid=afid,
                    affilname=affilname,
                    affiliation_city=affiliation_city,
                    affiliation_country=affiliation_country,
                    author_count=entry.get('author-count', {}).get('$'),
                    author_names=author_list,
                    # author_ids=author_ids,
                    # author_afids=author_afids,
                    coverDate=entry.get('prism:coverDate', ''),
                    coverDisplayDate=entry.get('prism:coverDisplayDate', ''),
                    publicationName=entry.get('prism:publicationName', ''),
                    issn=entry.get('prism:issn', ''),
                    source_id=entry.get('source-id', ''),
                    eIssn=entry.get('prism:eIssn'),
                    aggregationType=entry.get('prism:aggregationType', ''),
                    volume=entry.get('prism:volume', ''),
                    issueIdentifier=entry.get('prism:issueIdentifier', ''),
                    article_number=entry.get('article-number', ''),
                    pageRange=entry.get('prism:pageRange', ''),
                    description=entry.get('dc:description', ''),
                    authkeywords=entry.get('authkeywords', ''),
                    citedby_count=int(entry.get('citedby-count', 0)),
                    openaccess=int(entry.get('openaccess', 0)),
                    freetoread=freetoread,
                    freetoreadLabel=freetoreadLabel,
                    fund_acr=entry.get('fund-acr', ''),
                    fund_no=entry.get('fund-no', ''),
                    fund_sponsor=entry.get('fund-sponsor', ''),
                    url = entry.get('prism:url', '')
                )
                documents.append(doc)
            print('length of docs array:', len(documents))
            # print(documents[0])
            author_list = []
            for doc in documents:
                if doc.aggregationType == "Journal":
                    if doc.doi is not None:  # get abstract information in RIS format for a given DOI
                        #this will handle getting information from the api and then converting to ris to add to output file
                        # if doc[1] is not None:
                        citation = getAbstractRetrieval(doc[1], api_keys)
                        if citation:
                            citation += '\n'
                            outfile.write(citation)
                            
                            counting = counting + 1
                        else:
                            print('Error fetching abstract for DOI:', doc.doi)

                    else:
                        exception_count += 1
                        if doc.doi:
                            ris = f"TY  - JOUR\nTI  - {doc.title}\nJO  - {doc.publicationName}"\
                                f"\nVL  - {doc.volume}\nDA  - {doc.coverDate}\n"\
                                f"PY  - {doc.coverDate[0:4]}\nSP  - {doc.pageRange}\n"

                            if len(doc.author_names) != 0:
                                for au in doc.author_names:
                                    ris += f'AU  - {au}\n'

                            if doc.doi:
                                ris += f'DO  - {doc.doi}\nUR  - https://doi.org/{doc.doi}\n'

                            if doc.issueIdentifier:
                                ris += f'IS  - {doc.issueIdentifier}\n'

                            ris += 'ER  - \n\n'
                            outfile.write(ris)
                        else:
                            exceptions_list.append(f'Title: {doc.title}\nAuthors: {doc.author_names}\nType: {doc.aggregationType}\nSubtype: {doc.subtypeDescription}\nPublication Name: {doc.publicationName}\nDOI:{doc.doi}\n')

            print(f"Successfully generated references for {counting} journal articles.")
            if exception_count > 0:
                print(f"{exception_count} journal articles encountered errors and were handled separately. Check manually:")

                for item in exceptions_list:
                    print(item)

            chapter = 0
            book = 0

            for i in documents:
                if i.aggregationType != "Journal":
                    if i.subtypeDescription == "Book":
                        ris = f"TY  - BOOK\nTI  - {i.title}"\
                            f"\nDA  - {i.coverDate}\n"\
                            f"PY  - {i.coverDate[0:4]}\nSP  - {i.pageRange}\n"

                        if len(i.author_names) != 0:
                            for au in i.author_names:
                                ris += f'AU  - {au}\n'

                        if i.doi:
                            ris += f'DO  - {i.doi}\nUR  - https://doi.org/{i.doi}\n'

                        ris += 'ER  - \n\n'
                        outfile.write(ris)
                        book += 1

                    elif i.subtypeDescription == 'Book Chapter':
                        ris = f"TY  - CHAP\nTI  - {i.title}"\
                            f"\nT2  - {i.publicationName}\nDA  - {i.coverDate}\n"\
                            f"PY  - {i.coverDate[0:4]}\nSP  - {i.pageRange}\n"

                        if len(i.author_names) != 0:
                            for au in i.author_names:
                                ris += f'AU  - {au}\n'

                        if i.doi:
                            ris += f'DO  - {i.doi}\nUR  - https://doi.org/{i.doi}\n'

                        ris += 'ER  - \n\n'
                        outfile.write(ris)
                        chapter += 1

                    else:
                        ris = f"TY  - BOOK\nTI  - {i.title}"\
                            f"\nDA  - {i.coverDate}\n"\
                            f"PY  - {i.coverDate[0:4]}\nSP  - {i.pageRange}\n"

                        if len(i.author_names) != 0:
                            for au in i.author_names:
                                ris += f'AU  - {au}\n'

                        if i.doi:
                            ris += f'DO  - {i.doi}\nUR  - https://doi.org/{i.doi}\n'

                        ris += 'ER  - \n\n'
                        outfile.write(ris)
                        book += 1

            if book > 0 or chapter > 0:
                print(f"Generated {book} book references and {chapter} book chapter references.")

            outfile.close()

            end_time = datetime.now().replace(microsecond=0)
            print(f'\nTime to complete the search: {end_time - start_time}')
            return filename

    except IOError as io_err:
        print(f"File error occurred: {io_err}")

    except Exception as e:
        print(f"An unexpected error occurred (main scopus function): {e}")
    


@app.route('/scopus/download/<filename>', methods=['GET'])
@cross_origin(origin='localhost', headers=['Content-Disposition', 'Content-Type'])
def downloadFile(filename):
    try:
        # Ensure 'filename' is the correct relative path to the generated RIS file
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return str(e)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
