
#--@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#--@@@ MIF De-identifier by wsm 10/22/2019                                               
#--@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#--@@@ Purpose: De-identify MIFs exported from Maven                                       
#--@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#--@@@ Instructions: 
#--@@@ 		1. create folder and copy this file into it                  
#--@@@          2. in the same folder create three subfolders named MIF_With_PHI, 
#--@@@			MIF_Holding, and MIF_No_PHI (or whatever you think appropriate)
#--@@@		3. make sure all needed libraries are installed using pip. Some come with Python already, 
#--@@@			others don't. Just install the non-default ones. 	
#--@@@    	4. check the section "Set Vars" to ensure the folders you created in step 2 match the addresses
#--@@@          5. place individual exported cases containing PHI in the MIF_With_PHI folder i.e. 1 maven case per file				   per file x as many files as you like in the folder i.e. export one case at a time. 
#--@@@          6. execute script 
#--@@@          7. check the output folder MIF_No_PHI for your de-identified MIFs                           
#--@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@





import io
import os
from pathlib import Path
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

	logfile = open(summaryPath + 'MifDeindentifier_logfile_v' + logfileDateStamp + '.log','a') 

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
			item = root.find(xpathString).get(attributeName)
		except Exception as e:
			item = '--'

	else:	
		try:
			item = root.find(xpathString).text
		except Exception as e:
			item = '--'

	if item == None:
		item = '--'

	return item


##### Set Vars #####################################################

inputPath = 'K:\\Wes\\python\\projects\\MifDeidentifier\\MIF_With_PHI\\'
holdingPath = 'K:\\Wes\\python\\projects\\MifDeidentifier\\MIF_Holding\\'
outputPath = 'K:\\Wes\\python\\projects\\MifDeidentifier\\MIF_No_PHI\\'
summaryPath = 'k:\\wes\\python\\projects\\MifDeidentifier\\'


start_message = 'SCRIPT STARTED'
custom_logger(start_message)

##### Purge folders of any files ###################################

folder_purge(holdingPath)
folder_purge(outputPath)

##### copy files to holding folder ###################################

copy_or_move_files_to_folder(inputPath, holdingPath, 'COPY')

##### Crank through the files in holding folder##########################

for root, dirs, files in os.walk(holdingPath):  	

	for fileName in files: 						# iterate through all files in source folder 
		filePath = holdingPath + fileName	# create a string for the CDA document file name and folder location
		

##### Load MIF into xml object tree and parse ######################

		parser = etree.XMLParser(remove_blank_text=True)
		try:
			tree = etree.parse(filePath, parser)
		except Exception as e:
			parseMessage = filePath +': tree = etree.parse(inputfilePath, parser) --> '+ str(e) 
			custom_logger(parseMessage)
			continue

		try:
			root = tree.getroot()
		except Exception as e:
			getrootMessage = filePath+': root = tree.getroot() --> '+ str(e)
			custom_logger(getrootMessage)
			continue

##### Strip out namespaces in root element #########################

		for elem in root.getiterator():
			if not hasattr(elem.tag, 'find'): 
				custom_logger(filePath+': strip out namespaces in root element | if not hasattr(elem.tag, find): --> ')
				continue  

			i = elem.tag.find('}')
			if i >= 0:
				elem.tag = elem.tag[i+1:]
		objectify.deannotate(root, cleanup_namespaces=True)



##### Party and Address info ######################################################

		with open(filePath, 'r') as file:
			filedata = file.read()
			file.close()

		realCaseID = xml_retrieve('.//CaseDefinition','CaseID')  # also CaseDefinition ExternalID

		realFirstName = xml_retrieve('.//PartyDefinition', 'FirstName' )
		realMiddleName = xml_retrieve('.//PartyDefinition', 'MiddleName' )
		realLastName = xml_retrieve('.//PartyDefinition', 'LastName' )
		realFullName = xml_retrieve('.//PartyDefinition', 'FullName' )
		realBirthDate = xml_retrieve('.//PartyDefinition', 'BirthDate' )
		realTaxID = xml_retrieve('.//PartyDefinition', 'TaxID' )
		realExternalID = xml_retrieve('.//PartyDefinition', 'ExternalID' )

		realEmail = xml_retrieve('.//ContactPointDefinition',  'Email' )
		realStreet1 = xml_retrieve('.//ContactPointDefinition',  'Street1' )
		realStreet2 = xml_retrieve('.//ContactPointDefinition',  'Street2' )
		realPostalCode = xml_retrieve('.//ContactPointDefinition', 'PostalCode' ) 
		realHomePhone = xml_retrieve('.//ContactPointDefinition',  'HomePhone' )
		realMobilePhone = xml_retrieve('.//ContactPointDefinition',  'MobilePhone' )
		realWorkPhone = xml_retrieve('.//ContactPointDefinition',  'WorkPhone' )


		random.seed(realCaseID)
		randomCaseID = str(random.randrange(200000000,300000000))

		fake = Faker()
		fake.seed(realCaseID)	

		fakeFirstName = fake.first_name()
		fakeMiddleName = fake.first_name()
		fakeLastName = fake.last_name()
		fakeFullName = fakeFirstName + ' ' + fakeMiddleName + ' ' + fakeLastName
		fakeBirthDate = str(fake.date_of_birth())
		fakeTaxID = fake.ssn(taxpayer_identification_number_type='SSN')

		fakeEmail = fake.email()
		fakeStreet1 = fake.street_address()
		fakeStreet2 = ''
		fakePostalCode = fake.postalcode()
		fakeHomePhone = fake.numerify(text='(###) ###-####')
		fakeMobilePhone = fake.numerify(text='(###) ###-####')
		fakeWorkPhone = fake.numerify(text='(###) ###-####')
		fakeLatitude = '29.70'
		fakeLongitude = '-95.00'
		fakeTract = '12345'

		#fakeDate = fake.date(pattern="%Y-%m-%d", end_datetime=None)
		fakeDate1 = '1950-01-01'
		fakeDate2 = '01/01/1950'

		filedata = re.sub(r'FirstName="(?<=")([^"]+)(?=")"', 'FirstName="'+ fakeFirstName + '"', filedata)
		filedata = re.sub(r'MiddleName="(?<=")([^"]+)(?=")"', 'MiddleName="'+ fakeMiddleName + '"', filedata)
		filedata = re.sub(r'LastName="(?<=")([^"]+)(?=")"', 'LastName="'+ fakeLastName + '"', filedata)
		filedata = re.sub(r'FullName="(?<=")([^"]+)(?=")"', 'FullName="'+ fakeFullName + '"', filedata)
		filedata = re.sub(r'BirthDate="(?<=")([^"]+)(?=")"', 'BirthDate="'+ fakeBirthDate + '"', filedata)
		filedata = re.sub(r'TaxID="(?<=")([^"]+)(?=")"', 'TaxID="'+ fakeTaxID + '"', filedata)
		filedata = re.sub(r'Email="(?<=")([^"]+)(?=")"', 'Email="'+ fakeEmail + '"', filedata)
		filedata = re.sub(r'Street1="(?<=")([^"]+)(?=")"', 'Street1="'+ fakeStreet1 + '"', filedata)
		filedata = re.sub(r'Street2="(?<=")([^"]+)(?=")"', 'Street2="'+ fakeStreet2 + '"', filedata)
		filedata = re.sub(r'PostalCode="(?<=")([^"]+)(?=")"', 'PostalCode="'+ fakePostalCode + '"', filedata)
		filedata = re.sub(r'HomePhone="(?<=")([^"]+)(?=")"', 'HomePhone="'+ fakeHomePhone + '"', filedata)
		filedata = re.sub(r'MobilePhone="(?<=")([^"]+)(?=")"', 'MobilePhone="'+ fakeMobilePhone + '"', filedata)
		filedata = re.sub(r'WorkPhone="(?<=")([^"]+)(?=")"', 'WorkPhone="'+ fakeWorkPhone + '"', filedata)
		filedata = re.sub(r'Latitude="(?<=")([^"]+)(?=")"', 'Latitude="'+ fakeLatitude + '"', filedata)
		filedata = re.sub(r'Longitude="(?<=")([^"]+)(?=")"', 'Longitude="'+ fakeLongitude + '"', filedata)
		filedata = re.sub(r'Tract="(?<=")([^"]+)(?=")"', 'Tract="'+ fakeTract + '"', filedata)


###### Investigations ###################################################################### 

		investigations = root.xpath('.//InvestigationDefinition')  

		investigationCounter = 1
		for investigation in investigations:

			investigationExternalID = investigation.get('ExternalID')
			filedata = filedata.replace(investigationExternalID, 'ExternalID_Gobble-di-goop_' + str(investigationCounter), 1)

			investigationType = investigation.get('Type')
			filedata = filedata.replace(investigationType, 'Type_Gobble-di-goop_' + str(investigationCounter), 1)

			specimenDate = investigation.find('.//InvestigationResultDefinition[@ResultCode="SpecimenInfo"]/PropertyDefinition[@Name="SpecimenDate"]').get('Value')
			filedata = filedata.replace(specimenDate, fakeDate2)

			specimenNumber = investigation.find('.//InvestigationResultDefinition[@ResultCode="SpecimenInfo"]/PropertyDefinition[@Name="SpecimenNumber"]').get('Value')
			filedata = filedata.replace(specimenNumber, str(random.randrange(200000000,300000000)))

			resultDate = investigation.find('.//InvestigationResultDefinition[@ResultCode="Test"]').get('ResultDate')
			filedata = filedata.replace(resultDate, fakeDate1 + 'T00:00:00')

			medical_Record_Number = investigation.find('.//InvestigationResultDefinition[@ResultCode="Misc"]/PropertyDefinition[@Name="Medical_Record_Number"]').get('Value')
			filedata = filedata.replace(medical_Record_Number, '987654321')

			investigationCounter +=1

###### Double Checking For Any Hidden Elements ######################################################## 

		filedata = filedata.replace('"'+ realFirstName + '"', '"'+ fakeFirstName + '"')
		filedata = filedata.replace('"'+ realMiddleName + '"', '"'+ fakeMiddleName + '"')
		filedata = filedata.replace('"'+ realLastName + '"', '"'+ fakeLastName + '"')
		filedata = filedata.replace('"'+ realBirthDate + '"', '"'+ fakeBirthDate + '"')
		filedata = filedata.replace('"'+ realTaxID + '"', '"'+ fakeTaxID + '"')
		filedata = filedata.replace('"'+ realStreet1 + '"', '"'+ fakeStreet1 + '"')
		filedata = filedata.replace('"'+ realStreet2 + '"', '"'+ fakeStreet2 + '"')
		filedata = filedata.replace('"'+ realPostalCode + '"', '"'+ fakePostalCode + '"')
		filedata = filedata.replace('"'+ realHomePhone + '"', '"'+ fakeHomePhone + '"')
		filedata = filedata.replace('"'+ realMobilePhone + '"', '"'+ fakeMobilePhone + '"')
		filedata = filedata.replace('"'+ realWorkPhone + '"', '"'+ fakeWorkPhone + '"')
		filedata = filedata.replace('"'+ realEmail + '"', '"'+ fakeEmail + '"')


###### RiskDataDefinition Section ########################################################################### 

		filedata = re.sub(r'<RiskDataDefinition Iteration="0" QuestionID="BIRTH_DATE" Value="(?<=")([^"]+)(?=")"', '<RiskDataDefinition Iteration="0" QuestionID="BIRTH_DATE" Value="'+ fakeDate2 + '"', filedata)

		filedata = re.sub(r'<RiskDataDefinition Iteration="0" QuestionID="AGE" Value="(?<=")([^"]+)(?=")"', '<RiskDataDefinition Iteration="0" QuestionID="AGE" Value=""', filedata)

		filedata = re.sub(r'<RiskDataDefinition Iteration="0" QuestionID="AGE_YEARS" Value="(?<=")([^"]+)(?=")"', '<RiskDataDefinition Iteration="0" QuestionID="AGE_YEARS" Value=""', filedata)

		filedata = re.sub(r'<NoteDefinition Text="(?<=")([^"]+)(?=")"', '<NoteDefinition Text=""', filedata)


###### Write the new file in the output folder ################################################################# 

		with open(outputPath + 'Deidentified_' + fileName, 'w') as file:
			file.write(filedata)
			file.close()

###### empty the holding folder and quit################################################################# 

folder_purge(holdingPath)

print('\nend script')	
#wait = input("PRESS ENTER TO CONTINUE.")
