
#--@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#--@@@ ECR De-identifier by Wes McNeely 12/12/2019                                               
#--@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#--@@@ Purpose: De-identify raw eICRs from EPIC   
#--@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#--@@@ Process:    
#--@@@
#--@@@		1. find patient's real MRN and use as a basis for seeding faker module
#--@@@		2. locate names, birthdate, deathdate, MRN, and SSN for patient and replace with fakes
#--@@@		3. locate and replace names for emergency contacts and guardian of patient and replace with fakes
#--@@@		4. locate ALL physical addresses, phone numbers, fax numbers, and email addresses and replace with fakes 
#--@@@		5. locate ALL times and dates and replace with fakes
#--@@@		6. locate and REMOVE ALL section "text" elements. These elements are used in the XHTML "display" 
#--@@@			portion of the eICR and have free form narratives that could contain PHI.   
#--@@@		
#--@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#--@@@ Instructions: 
#--@@@		
#--@@@ 		1. create folder and copy this file into it                  
#--@@@      2. in the same folder create three subfolders named "with_PHI", 
#--@@@			"holding", and n"o_PHI" (or whatever you think appropriate)
#--@@@		3. make sure all needed libraries are installed using pip. Some come with Python already, 
#--@@@			others don't. Just install the non-default ones. 	
#--@@@    	4. check the section "Set Vars" to ensure the folders created in step 2 match
#--@@@      5. place individual exported cases containing PHI in the MIF_With_PHI folder i.e. 1 maven case 
#--@@@ 			per file x as many files as you like in the folder i.e. export one case at a time. 
#--@@@      6. execute script 
#--@@@      7. check the output folder "no_PHI" for your de-identified MIFs                           
#--@@@		
#--@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#--@@@  Update:
#--@@@  	
#--@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

import os
import sys
import shutil
from shutil import copyfile as copy_file
from shutil import move as move_file
import csv
import datetime as DT
import time
import xml.dom.minidom as MD
from lxml import etree, objectify
from lxml.builder import ElementMaker
from faker import Faker
import re
import random

def custom_logger(message=None):

	logfileDateStamp=DT.datetime.today().strftime('%Y%m%d')
	messageTimeStamp=DT.datetime.today().strftime('%m-%d-%Y %H:%M:%S')

	logfile = open(summaryPath + 'eICR_Deidentifier_logfile_v' + logfileDateStamp + '.log','a') 

	logEntry ='[' + messageTimeStamp + '] ' + message + '\n'
	logfile.write(logEntry) 

	logfile.close() 

	return

def copy_or_move_files_to_folder(startingFolderPath, destinationFolderPath, copy_or_move):

	print('')

	for root, dirs, files in os.walk(startingFolderPath):  	# compile list of all files in source folder
		#fileCount = str(len(files))

		for fileName in files: 						# iterate through all files in source folder 
			FromFilePath =	startingFolderPath + fileName	
			ToFilePath =	destinationFolderPath + fileName	


			if copy_or_move == 'COPY':
				copy_file(FromFilePath, ToFilePath)
				print('COPYING...')	

			elif copy_or_move == 'MOVE':
				move_file(FromFilePath, ToFilePath)
				print('MOVING...')

			print('From: '+ FromFilePath)
			print('To: ' + ToFilePath)
			print('')

			loggerMessage = copy_or_move + ' FILE: ' + FromFilePath + ' --> ' + ToFilePath
			custom_logger(loggerMessage)

def folder_purge(folderPath):

	print('')
	print('Purging')
	print('')
	#make sure the clean folder is empty
	for the_file in os.listdir(folderPath):
	    file_path = os.path.join(folderPath, the_file)
	    try:
	        if os.path.isfile(file_path):
	            os.unlink(file_path)
	    except Exception as e:
	        print(e)
	print(folderPath, 'purged')
	print('')	

	loggerMessage = 'PURGE FOLDER: ' + folderPath
	custom_logger(loggerMessage)

def xml_retrieve(xpathString, attributeName=None):   	#function to retrieve element text or attributes 
	if not attributeName == None:						#attribute name is optional, if ommitted it looks for text
		try:
			item = rootEl.find(xpathString).get(attributeName)
		except Exception as e:
			item = ''

	else:	
		try:
			item = rootEl.find(xpathString).text
		except Exception as e:
			item = ''

	if item == None:
		item = ''

	return item

def xml_change(rootElement, xpathString, replacementValue, attributeName=None, isIterable=False):   	#function to alter element text or attributes 


	if isIterable == False:							#isIterable is optional, if omitted it looks for first element only
		if not attributeName == None:						#attributeName is optional, if omitted it looks for text
			try:
				rootElement.find(xpathString).set(attributeName,replacementValue)
				#elem.text = replacementValue
			except Exception as e:
				custom_logger(str(e))

		else:	
			try:
				rootElement.find(xpathString).text = replacementValue
			except Exception as e:
				custom_logger(str(e))

	else:	
		if not attributeName == None:						
			try:
				for el in rootElement.xpath(xpathString):
					el.set(attributeName,replacementValue)					
			except Exception as e:
				custom_logger(str(e))

		else:	
			try:
				for el in rootElement.xpath(xpathString):
					el.text = replacementValue
			except Exception as e:
				custom_logger(str(e))

def xml_remove(xpathString, elementToRemove):   	#function to remove entire element 

	for elementToSearch in rootEl.xpath(xpathString):
		elementToSearch.remove(elementToSearch.find(elementToRemove))

##### Set paths and variables #####################################################

inputPath = 'K:\\Wes\\python\\projects\\ECR_Deidentifier\\CDA\\'
holdingPath = 'K:\\Wes\\python\\projects\\ECR_Deidentifier\\holding\\'
outputPath = 'K:\\Wes\\python\\projects\\ECR_Deidentifier\\no_PHI\\'
summaryPath = 'k:\\wes\\python\\projects\\ECR_Deidentifier\\'

timestampString=DT.datetime.today().strftime('%Y%m%d%H%M%S')
namespace_SDTC = {'s': 'urn:hl7-org:sdtc'}


start_message = 'SCRIPT STARTED'
custom_logger(start_message)

##### Purge folders of any files ###################################

folder_purge(holdingPath)
folder_purge(outputPath)

##### Copy files to holding folder ###################################

copy_or_move_files_to_folder(inputPath, holdingPath, 'COPY')

##### Crank through the files in holding folder##########################

for root, dirs, files in os.walk(holdingPath):  	

	for fileName in files: 						# iterate through all files in source folder 
		filePath = holdingPath + fileName	# create a string for the CDA document file name and folder location
		

##### Load eICR into xml object tree and parse ######################

		parser = etree.XMLParser(remove_blank_text=True)
		try:
			tree = etree.parse(filePath, parser)
			#print(tree)
		except Exception as e:
			parseMessage = filePath +': tree = etree.parse(inputfilePath, parser) --> '+ str(e) 
			custom_logger(parseMessage)
			continue

		try:
			rootEl = tree.getroot()
			#print(root)
		except Exception as e:
			getrootMessage = filePath+': root = tree.getroot() --> '+ str(e)
			custom_logger(getrootMessage)
			continue

##### Strip out namespaces in root element #########################

		for elem in rootEl.getiterator():
			if not hasattr(elem.tag, 'find'): 
				custom_logger(filePath+': strip out namespaces in root element | if not hasattr(elem.tag, find): --> ')
				continue  

			i = elem.tag.find('}')
			if i >= 0:
				elem.tag = elem.tag[i+1:]
				#print(elem.tag)
		objectify.deannotate(rootEl, cleanup_namespaces=True)



##### Create and seed the faker ######################################################

		patientMRN = xml_retrieve('.//recordTarget/patientRole/id[@assigningAuthorityName="EMRN"]','extension')
			
		fake = Faker()
		fake.seed(int(patientMRN)+73952064)	# seed the faker with the (obfuscated) MRN to get consistent fake results

##### Change names, dates, etc ######################################################

		xml_change(rootEl,'.//recordTarget/patientRole/patient/name/given', fake.first_name(), None, True)
		xml_change(rootEl,'.//recordTarget/patientRole/patient/name/given[2]', fake.first_name(), None, True)
		xml_change(rootEl,'.//recordTarget/patientRole/patient/name/given[3]', fake.first_name(), None, True)
		xml_change(rootEl,'.//recordTarget/patientRole/patient/name/family', fake.last_name(), None, True)
		xml_change(rootEl, './/recordTarget/patientRole/id[@assigningAuthorityName="EMRN"]', str(random.randrange(600000000,700000000)),'extension')
		xml_change(rootEl, './/recordTarget/patientRole/id[@assigningAuthorityName="Social Security Administration"]', fake.ssn(taxpayer_identification_number_type="SSN"),'extension')
		xml_change(rootEl, './/birthTime', str(fake.date_of_birth()), 'value' )
		xml_change(rootEl, './/deceasedTime', str(fake.date_of_birth()), 'value')

		xml_change(rootEl,'.//recordTarget/patientRole/patient/guardian/guardianPerson/name/given', fake.first_name())
		xml_change(rootEl,'.//recordTarget/patientRole/patient/guardian/guardianPerson/name/family', fake.last_name())

		xml_change(rootEl,'.//participant/associatedEntity/name/given', fake.first_name())
		xml_change(rootEl,'.//participant/associatedEntity/name/family', fake.last_name())

		xml_change(rootEl, './/telecom[contains(@value,"tel")]', "tel:" + fake.phone_number(), 'value', True)
		xml_change(rootEl, './/telecom[contains(@value,"fax")]', "fax:" + fake.phone_number(), 'value', True)
		xml_change(rootEl, './/telecom[contains(@value,"mailto")]', "mailto:" + fake.email(), 'value', True)
		xml_change(rootEl, './/streetAddressLine', fake.street_address(), None, True)
		xml_change(rootEl, './/postalCode', fake.postalcode(), None, True)

		xml_change(rootEl, './/effectiveTime/low', DT.datetime.today().strftime('%Y%m%d%H%M%S'), 'value', True)
		xml_change(rootEl, './/effectiveTime/high', DT.datetime.today().strftime('%Y%m%d%H%M%S'), 'value', True)
		xml_change(rootEl, './/time', DT.datetime.today().strftime('%Y%m%d%H%M%S'), 'value', True)

##### Remove all section <text> areas  ######################################################

		xml_remove('/ClinicalDocument/component/structuredBody/component/section', 'text')
		xml_remove('/ClinicalDocument/component/structuredBody/component/section/entry/substanceAdministration', 'text')

##### Write the new file in the output folder ################################################################# 

		xmlObject = etree.tostring(tree).decode()
		xmlReparsed = MD.parseString(xmlObject)
		xmlIndented = xmlReparsed.toprettyxml(indent='\t')

		#outputfilePath = outputPath + 'Deidentified_'+ fileName + '_v' + timestampString + '.xml'    #create new filename for pretty xml
		outputfilePath = outputPath + 'Deidentified_'+ fileName + '.xml'    #create new filename for pretty xml
		outputfilePathContents = open(outputfilePath, 'w') 

		try: 
		    print(xmlIndented, file = outputfilePathContents)  
		except Exception as e:
		    print('\t', fileName, '\n', '\t', e)
		    #exit()

		outputfilePathContents.close()
		writeMIF_message = 'WRITE eICR: ' + outputfilePath
		custom_logger(writeMIF_message)


###### empty the holding folder and quit################################################################# 

folder_purge(holdingPath)

print('\nend script')	
