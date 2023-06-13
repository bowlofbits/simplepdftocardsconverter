import sys, fitz
import re



def all_equal(iterator):
    iterator = iter(iterator)
    try:
        first = next(iterator)
    except StopIteration:
        return True
    return all(first == x for x in iterator)


def getweightedfontncolorstatisticsofdoc(doc):
    """PDF statistics regarding font and color
    :param page: page of docment
    :return: {font:count}{color:count}
    """
    colorstats={}
    fontstats={}
    linecount=0.0
    for page in doc:
        blocks= page.get_text("dict")["blocks"]
        
        #get statistics of color and fonts 
        for b in blocks:
            if b["type"] == 0:  # this block contains text
                for l in b["lines"]:
                    for s in l["spans"]:
                        if not s['text'].isspace():#do not count empty text elements
                            # print(s)
                            # print(s['color'])
                            if s['color'] in colorstats:
                                colorstats[s['color']]=colorstats[s['color']]+1
                            else:
                                colorstats[s['color']]=1.0
                            if s['font'] in fontstats:
                                fontstats[s['font']]=fontstats[s['font']]+1
                            else:
                                fontstats[s['font']]=1.0
                                #artificially increase the size of the element
                            linecount+=1
    #calcstatistics
    for k,c in colorstats.items():
        colorstats[k]=c/linecount
    for r,sq in fontstats.items():
        fontstats[r]=sq/linecount

    return fontstats,colorstats

def getblockswithgranularityColorFont(page,fontstats,colorstats,usefontsNcolor):
    """Extracts blocks using color and font in addition to size.
    :param page: page of doc
    :param fontstats: statistics of the fonts
    :param fontstats: statistics of the color
    :type doc: <class 'fitz.fitz.Document'>
    :param granularity: also use 'font', 'flags' and 'color' to discriminate text
    :type granularity: bool
    :rtype: page blocks 
    :return: blocks
    """
    rat = 1.618*1
    if usefontsNcolor:
        blocks= page.get_text("dict")["blocks"]

        #augment the font sizes
        for b in blocks:
            if b['type'] == 0:  # this block contains text
                applyfontcolorrezize=False
                #only apply size augmentation of enitre line has the same properties
                for l in b['lines']:
                    fontlist=[s['font'] for s in l["spans"] if not s['text'].isspace()]
                    colorlist=[s['color'] for s in l["spans"]if not s['text'].isspace()]
                if all_equal(fontlist) and all_equal(colorlist):
                    applyfontcolorrezize=True
                    #print("allcolorline is true for:",l)
                for l in b['lines']:
                    for s in l["spans"]:
                        size=float(s['size'])
                        if applyfontcolorrezize and not s['text'].isspace():
                            s['size']= size*size+ size *(1/colorstats[s['color']])#+ 0.5*size *(1/fontstats[s['font']]) 
                        else:
                            s['size']= size*size
                 
        return blocks
    else:
        return page.get_text("dict")["blocks"]

    #go through blocks and if color != 


def fonts(doc,fontstats,colorstats,usefontsNcolor):
    """Extracts fonts and their usage in PDF documents.
    :param doc: PDF document to iterate through
    :type doc: <class 'fitz.fitz.Document'>
    :param granularity: also use 'font', 'flags' and 'color' to discriminate text
    :type granularity: bool
    :rtype: [(font_size, count), (font_size, count}], dict
    :return: most used fonts sorted by count, font style information
    """
    styles = {}
    font_counts = {}

    for page in doc:
        #blocks = page.get_text("dict")["blocks"]
        blocks = getblockswithgranularityColorFont(page, fontstats,colorstats,usefontsNcolor)
        for b in blocks:  # iterate through the text blocks
            if b['type'] == 0:  # block contains text
                for l in b["lines"]:  # iterate through the text lines
                    for s in l["spans"]:  # iterate through the text spans
                        if usefontsNcolor:
                            identifier = "{0}_{1}_{2}_{3}".format(s['size'], s['flags'], s['font'], s['color'])
                            styles[identifier] = {'size': s['size'], 'flags': s['flags'], 'font': s['font'],
                                                  'color': s['color']}
                        else:
                            identifier = "{0}".format(s['size'])
                            styles[identifier] = {'size': s['size'], 'font': s['font']}

                        font_counts[identifier] = font_counts.get(identifier, 0) + 1  # count the fonts usage

    font_counts = sorted(font_counts.items(), key=lambda ele:ele[1], reverse=True) #fo whatever reason, get the second element as key (passed as a function)

    if len(font_counts) < 1:
        raise ValueError("Zero discriminating fonts found!")

    return font_counts, styles

def font_tags(font_counts, styles):
    """Returns dictionary with font sizes as keys and tags as value.
    :param font_counts: (font_size, count) for all fonts occuring in document
    :type font_counts: list
    :param styles: all styles found in the document
    :type styles: dict
    :rtype: dict
    :return: all element tags based on font-sizes
    """
    p_style = styles[font_counts[0][0]]  # get style for most used font by count (paragraph)
    p_size = p_style['size']  # get the paragraph's size

    # sorting the font sizes high to low, so that we can append the right integer to each tag 
    font_sizes = []

    #print("font_counts:",font_counts)
    for (font_size, count) in font_counts:
        #print("fontsize:",font_size, " count:", count)
        if "_"in font_size: #special handling if granularity in function fonts is set to true
            font_sizes.append(float(font_size.split("_")[0]))
        else:
            font_sizes.append(float(font_size))

    font_sizes.sort(reverse=True)
    print('fontsize:',font_sizes)
    # aggregating the tags for each font size
    idx = 0
    size_tag = {}
    for size in font_sizes:
        idx += 1
        if size == p_size:
            idx = 0
            size_tag[size] = '<p>'
        if size > p_size:
            size_tag[size] = '<h{0}>'.format(idx)
        elif size < p_size:
            size_tag[size] = '<s{0}>'.format(idx)

    return size_tag

def headers_para(doc, size_tag,fontstats,colorstats,usefontsNcolor):
    """Scrapes headers & paragraphs from PDF and return texts with element tags.
    :param doc: PDF document to iterate through
    :type doc: <class 'fitz.fitz.Document'>
    :param size_tag: textual element tags for each size
    :adds pagemarker PJ
    :type size_tag: dict
    :rtype: list
    :return: texts with pre-prended element tags
    """
    header_para = []  # list with headers and paragraphs
    first = True  # boolean operator for first header
    previous_s = {}  # previous span
    pcount=1

    for page in doc:
        header_para.append("<-Page "+str(pcount)+">")
        pcount+=1
        #blocks = page.get_text("dict")["blocks"]
        blocks = getblockswithgranularityColorFont(page, fontstats,colorstats,usefontsNcolor)
        for b in blocks:  # iterate through the text blocks
            if b['type'] == 0:  # this block contains text
                #print("block:",b)
                # REMEMBER: multiple fonts and sizes are possible IN one block

                block_string = ""  # text found in block
                for l in b["lines"]:  # iterate through the text lines
                    for s in l["spans"]:  # iterate through the text spans
                        if s['text'].strip():  # removing whitespaces:
                            #print("block:",b,"\n")
                            if first:
                                previous_s = s
                                first = False
                                block_string = size_tag[s['size']] + s['text']
                            else:
                                if s['size'] == previous_s['size']: # connect all elements as long as they are of the same size

                                    if block_string and all((c == "|") for c in block_string):
                                        # block_string only contains pipes
                                        block_string = size_tag[s['size']] + s['text']
                                    if block_string == "":
                                        # new block has started, so append size tag
                                        block_string = size_tag[s['size']] + s['text']
                                    else:  # in the same block, so concatenate strings
                                        block_string += " " + s['text']

                                else: # this code only switches size tag if size changes, independent of the the color etc. 
                                    header_para.append(block_string)
                                    block_string = size_tag[s['size']] + s['text']

                                previous_s = s

                    # new block started, indicating with a pipe
                    #block_string += "|"

                header_para.append(block_string)

    return header_para


#def turntexttocards(headerspara,chunksize=500,overlap=50):
def finishcard(validheaders,metadata,cardtext):
    # helper function for buildcards finish previous card
    
    card={}
    card["metadata"]={}
    card["metadata"]["source"]= metadata[0]+" "+''.join(metadata[1])
    card["metadata"]["title"]= ' '.join(validheaders)
    card["page_content"]=cardtext
    
    return card

def buildcards(headerspara, filename,headerdepth):
    """From marked text that includes html header markings, this function builds a series of text blocks .
    :param headerspara: text with html header markings 
    :param filename: name of the pdf file processed / source
    :param headerdepth: lvl of header which shall be includd in the title of a text block e.g. 4 means up to <h4>
    :return: "cards" with a [{"page_content": text, "metadata":{"source":, "title"}} ]
    """
    validheaders=[]
    i=0
    while i<=headerdepth: 
        validheaders.append("")
        i+=1
    metadata=[]
    metadata.append(filename)
    metadata.append([])
    cards=[]
    block={}
    text=""
    blocktext=""
    for ele in headerspara:
        
        #handle the page metadata, split the block on pagebreak
        if "<-Page " in ele:
            
            # finish previous card
            cards.append(finishcard(validheaders,metadata,blocktext))
            #reset 
            blocktext=""

            #set the page
            metadata[1]=ele.replace("-","").replace("<","").replace(">","")
            continue

        if '>' not in ele:
            continue
        #handle header
        #if new detected, start a new block, close the old one and append it, ignore everything 
    
        rawdem,text = ele.split(">",1)
        
        denominator =re.sub("[^0-9]", "", rawdem)

        if denominator !="" and denominator.isnumeric() and "<h" in rawdem and int(denominator)<=headerdepth:
            # finish previous card
            denominator = int(denominator)
            
            cards.append(finishcard(validheaders,metadata,blocktext))
            #reset 
            blocktext=""
            #set the header
            validheaders[denominator]=text
            #clear all lower headers
            i=denominator+1
            while i<=headerdepth: 
                validheaders[i]=""
                i+=1  

        blocktext=blocktext+text

    # go through the cards and split the text if 
    return cards

def splitcards(cards,maxcardcharacterlength,overlap):
    # split card page content to ensure a mximum text length with an overlap to previous text
    result = []
    keytobesplit='page_content'
    for card in cards:
        value =""
        value = card[keytobesplit]
        
        if len(value) > maxcardcharacterlength:
         
            i = 0
            splitdicts=[]
            while i < len(value):
                end = i + maxcardcharacterlength
              
                # adjust end index to avoid word split
                while end < len(value) and value[end] != ' ':
                    end -= 1
                # if we reached the start of the substring without finding a space
                # then we forcibly split the word to meet the length limit
                if end == i:
                    end = i + maxcardcharacterlength
                new_entry={}
                new_entry=card.copy()
                new_entry[keytobesplit] = value[i:end]
                splitdicts.append(new_entry)
                
                i = end - overlap if end - overlap > i else end
                #go back to the lastest space
                while i>0 and abs(end-i)<overlap*2 and i<len(value) and value[i] != ' ':
                     i-=1
         
            result.extend(splitdicts)
        else:
            result.append(card)
    return result

def selectsmallestheadinglvl(size_tag):
    """Select suitable headinging depth .
    :param size_tag: statistics about the pdf fonts  
    :return: selected heading lvl->  lvl of header which shall be includd in the title of a text block e.g. 4 means up to <h4>
    """
    count=0
    rat=1.618
    headings  = {key: value for key, value in size_tag.items() if 'h' in value}
    sorted_values = sorted(headings.keys(), reverse=True)
    
    smallestfont=999
    if len(sorted_values)>1:
        smallestfont= float(sorted_values[1])/rat

    elif len(sorted_values)==1:
        smallestfont=float(sorted_values[0])/rat

    filteredVal= filter(lambda x: x>smallestfont, sorted_values)
    #print("filteredvals:", type(min(filteredVal)))
    fV=min(filteredVal)
    print("smallestfont:",smallestfont)
    selected=size_tag[fV]#[k for k,x in size_tag.items() if float(k)==fV]
    print("selected:", selected)
    
    print(size_tag)
    #print("selectedsize:", int(size_tag[min(filteredVal)].replace("<h","").replace(">","")))
    
    #a=qw
    try:
        return int(selected.replace("<h","").replace(">","")) #re.sub("[^0-9]", "", size_tag[min(filteredVal)])
    except:
        return 3 #default

def charactercleanup(text):
    return ''.join(c for c in text if c.isprintable()) #c.isalnum() or c.isspace() or c in '.,?!<>' or


def convertpdftocards(pdfpath,maxcardcharacterlength,overlap, usefontsNcolor=True ):
    """turn pdf into text blocks / "cards" as if a human would read the document and split it into cards for memorizing and organizing the text.
     This function splits text along headings and page breaks 
    :param pdfpath: path to pdf
    :param maxcardcharacterlength: max size of card
    :param overlap: overlap between textblocks
    :param usefontsNcolor: use fonts and color as distinguishing characteristics to detect headers
    :return: pdf split in cards by detected header
    """ 
    


    print("PDFtoCards: ",pdfpath)
    doc = fitz.open(pdfpath)  # open document

    fontstats,colorstats=getweightedfontncolorstatisticsofdoc(doc)

    font_counts, styles=fonts(doc,fontstats,colorstats,usefontsNcolor)
    for k,s in styles.items():
        print("style:",s)
    size_tag =font_tags(font_counts, styles)

    headinglvl=selectsmallestheadinglvl(size_tag)
    #print(headinglvl)
    result = headers_para(doc,size_tag,fontstats,colorstats,usefontsNcolor)

    #print("\n",result)
    
    #remove the - binding word in linebreaks
    cresults=[]
    for ele in result:
       t=re.sub(r'([a-zA-Z])- ([a-z])', r'\1\2', ele)
       cresults.append(charactercleanup(t))

    cards= buildcards(cresults, pdfpath,headinglvl)
    scards=splitcards(cards,maxcardcharacterlength,overlap)
    return  [x for x in scards if not x['page_content'].isspace()]

# def main():
    
#     #source_directory = os.environ.get('SOURCE_DIRECTORY', 'source_documents')
#     #file_path = "E:/WinPrivateGPT/privateGPT/source_documents/link-Einzelabschluss_TKAG_2019_2020_EN.pdf"
#     scards= pdftocardsconverter(file_path,500,50 )
#     for c in scards:
#        asd=1
#        print(c,"\n\n")

# if __name__ == "__main__":
#     main()



# fname = "E:/WinPrivateGPT/privateGPT/source_documents/link-Einzelabschluss_TKAG_2019_2020_EN.pdf" #sys.argv[1]  # get document filename
# doc = fitz.open(fname)  # open document
# out = open("test.txt", "wb")  # open text output
# for page in doc:  # iterate the document pages
#     #text = page.get_text().encode("utf8")  # get plain text (is in UTF-8)
#     text = page.get_text("html")
#     print(text)
#     #print(text)
#     for e in text[:20]:
#         #print(e)
#         if isinstance(e, str):
#             out.write(str(e))  # write text of page
#         #out.write("\nblockEnd\n")
#     #out.write(bytes((12)))  # write page delimiter (form feed 0x0C)
# out.close()