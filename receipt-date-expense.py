##################
#IMPORT STATEMENTS
##################
import boto3
import io
import re
import json
import tkinter as tk
import time
import PIL
import matplotlib.pyplot as plt
import matplotlib
import pandas as pd
from time import gmtime, strftime
from string import digits
from dateutil import parser
from tkinter import filedialog
from PIL import Image,ImageTk,ImageFilter,ImageOps
matplotlib.style.use('ggplot')



root = tk.Tk()
images = []



#########################
#PROCESSING RECEIPT
#########################
def process_receipt(filename, 
                    bucket = 'textract-date-expense-tracker-2', 
                    display=False, upload=True, printout=False):
    ###################################
    #CREATING OBEJECTS AND VARIABLES
    ###################################
    s3_object = boto3.resource('s3').Object(bucket, filename)
    s3_response = s3_object.get()
    stream = io.BytesIO(s3_response['Body'].read())
    bucket_location = boto3.client('s3').get_bucket_location(Bucket=bucket)
    ###################
    #INVOKING TEXTRACT
    ###################
    text = boto3.client('textract')
    image_binary = stream.getvalue()
    response = text.detect_document_text(Document={'Bytes': image_binary})

    dates = []
    totals = []
    
    for i, block in enumerate(response["Blocks"]):
        if block["BlockType"] == "LINE":
            #########################################################
            #SEARCHING FOR DATE AND TOTAL AMOUNT FROM TEXTRACTED DATA
            #########################################################
            date = re.search("[0-3]?[0-9]/[0-3]?[0-9]/(?:[0-9]{2})?[0-9]{2}", block["Text"])
            total = re.search("Total|TOTAL", block["Text"])

            if date is not None: 
                dates.append(date.group())

            if total is not None: 
                total = ''.join(c for c in response["Blocks"][i+1]["Text"] if c in digits+"."+",")
                if total == '':
                    total = ''.join(c for c in response["Blocks"][i-1]["Text"] if c in digits+"."+",")
                totals.append(total.replace(",", "."))
    ######################
    #SETTING DATE WRT FILE 
    ######################
    try :
        date = list(set(dates))[0]
        dt = parser.parse(date)
        date = dt.strftime("%Y-%m-%d")
    except :
        date = None
    #######################
    #SETTING TOTAL WRT FILE 
    #######################
    try :
        amount = list(set(totals))[0]
    except :
        amount = None
    ############################
    #DISPLAYING IMAGE ON CONSOLE
    ############################
    if display: 
        image = Image.open(stream)
        fig, ax = plt.subplots(figsize=(5,10))
        ax.imshow(image)
        plt.show()
        
    
    #############################
    #DISPLAYING RESULT ON CONSOLE
    #############################
    if printout:
        print ("Document: ",filename,"Date: ",date," Amount: ",amount)
        #############################
        #DISPLAYING RESULTS ON WIDGET
        #############################
        label2 = tk.Label(frame, text="Date: "+date+" Amount: "+amount, bg="gray")
        label2.pack()
    
    #################################
    #DATA FOR JSON WITH RESPECT TO S3
    #################################
    content = {            
            'receipt' : "https://textract-date-expense-tracker-2.s3-ap-southeast-1.amazonaws.com/",
            'submitted_on' : strftime("%Y-%m-%d %H:%M:%S GMT", gmtime()),
            'date' : date,
            'amount' : amount
    }
    #########################
    #CREATING JSON OF IMAGE
    #########################
    if upload: 
        boto3.client('s3').put_object(Body=json.dumps(content), Bucket=bucket, Key="image-jsons/"+filename.replace("jpeg", "json"));
    
    return



#########################
#UPLOADING IMAGE FUNCTION
#########################
def uploadImage():
    ##################################################
    #DESTROYING REPEATED OPENED FILE NAMES FROM WIDGET
    ##################################################
    for widget in frame.winfo_children():
        widget.destroy()
    #########################
    #ASKING FOR FILE
    #########################
    filename = filedialog.askopenfilename(initialdir="/", title="Select JPEG image", filetypes=(("images","*.jpeg"),("all files","*.*")))
    images.append(filename)
    print(filename)
    #########################
    #UPLOADING FILE
    #########################
    for image in images:
        client = boto3.client('s3', region_name='ap-southeast-1')
        client.upload_file(image, 'textract-date-expense-tracker-2', image)
        #########################
        #DISPLAYING FILE NAME
        #########################
        label3 = tk.Label(frame, text=image)
        Image.open(filename)
        label3.pack()
        
        
        
#########################
#RESULT BUTTON  FUNCTION
#########################
def runImage():
    #################################
    #CALLING PROCESS_RECEIPT FUNCTION
    #################################
    for image in images:
        process_receipt(image, display=True, upload=False, printout=True)
        

#########################
#CREATING CANVAS (WIDGET)
#########################
canvas = tk.Canvas(root, height = 500, width = 500, bg = "#263D42")
canvas.pack()
#########################
#CREATING FRAME IN CANVAS
#########################
frame = tk.Frame(root, bg="white")
frame.place(relwidth=0.8, relheight=0.8, relx=0.1, rely=0.1)
#########################
#DEFINING UPLOAD BUTTON
#########################
openFile = tk.Button(root, command=uploadImage, text="Upload jpeg", padx=10, pady=5, fg="white", bg="#263D42")
openFile.pack()
#########################
#DEFINING RESULT BUTTON
#########################
result = tk.Button(root, command=runImage, text="Result", padx=10, pady=5, fg="white", bg="#263D42")
result.pack()
#########################
#DEFINING RESULT BUTTON
#########################
root.mainloop()



'''

#########################################
#RUNNING ON ALL RECEIPTS GIVEN IN TASK
#########################################
s3 = boto3.resource('s3')
bucket = s3.Bucket('textract-date-expense-tracker-2')
for i, receipt in enumerate(bucket.objects.filter()):
    if ".jpeg" in receipt.key:
        if i % 1 == 0:
            process_receipt(receipt.key, printout=True, display=True)
        else:
            process_receipt(receipt.key, printout=True)
        time.sleep(2)
###########################
#CHECKING JSON OUTPUT IN S3
###########################
s3 = boto3.resource('s3')
content_object = s3.Object('textract-date-expense-tracker-2', 'image-jsons/receipt111.json')
file_content = content_object.get()['Body'].read().decode('utf-8')
json_content = json.loads(file_content)
print(json.dumps(json_content, indent=2))
############################
#PLOTTING EXPENSES OVER TIME
############################
jsons = []
for extract in bucket.objects.filter():
    if ".json" in extract.key:
        content_object = s3.Object(extract.bucket_name, extract.key)
        file_content = content_object.get()['Body'].read().decode('utf-8')
        jsons.append(json.loads(file_content))
##################
#CREATIN DATAFRAME
##################
expenses = pd.concat([pd.DataFrame(j, index=[0]) for j in jsons], ignore_index=True)
#####################
#CALCULATING ACCURACY
#####################
nulls = expenses.date.isna().sum()
accuracy = ((581-nulls)/581)*100
'''

####
#EOF
####
