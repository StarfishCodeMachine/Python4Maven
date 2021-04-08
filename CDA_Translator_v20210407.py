#--@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#--@@@ Document Name: CDA Translator for Maven by Wes McNeely 04/07/2021                                            
#--@@@ Description:	Python code for translation/mapping of CDA/eICR documents to HEDSS/Maven formatted files for ingestion
#--@@@ Purpose: De-identify eICRs from Epic and insert into Maven Test environment                                      
#--@@@ Document Owner:		City of Houston Health Department
#--@@@ Document Creator:	Wesley McNeely, MS, MPH wesley.mcneely@houstontx.gov
#--@@@							Informatics Supervisor, Division of Disease Prevention and Control
#--@@@							Houston Health Department
#--@@@							832-393-5080 (main) | 832-393-5052 (desk) | 281-433-7934 (cell)
#--@@@							8000 N. Stadium Drive, 4th floor| Houston, TX 77054
#--@@@
#--@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#--@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#--@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#--@@@ Instructions: 
#--@@@ 				1. create a folder and copy this file into it                  
#--@@@              2. in the same folder create four subfolders: MIF, CSV, EICR, LOGS 
#--@@@				3. on the Maven app server create three foldera for ingesting MIFs called INPUT, ARCHIVE, and ERROR
#--@@@    			4. in the Maven application create a "Data Import Processor" processing module with folder locations that
#--@@@    				match step 3
#--@@@              5. make sure all the necessary Python libraries are installed 
#--@@@              6. place raw eICRs into the folder you named EICR 
#--@@@              6. execute this script 
#--@@@              7. check the server folder INPUT that will contain the de-identified MIFs and enable the 
#--@@@              	"Data Import Processor" processing module                          
#--@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#--@@@  Notes:
#--@@@  			To use this code to import eICRs into a production environment, comment out commands in the 
#--@@@  				"Deidentification using Faker" section of this code starting at ~line 590. Be aware this will
#--@@@  				mess up the CSV logging aspect of the code which will have to be modified or commented out.   
#--@@@  
#--@@@				Please also note the xPaths in this script reflect a sometimes imperfect understanding   
#--@@@ 					of the Implementation Guide -->
#--@@@						HL7 CDA® R2 Implementation Guide: Public Health Case Report, Release 2
#--@@@ 						Standard for Trial Use Release 1.1
#--@@@ 						December 2016
#--@@@ 					and were tailored to match xPaths found in Epic-derived  
#--@@@  				eICRs. Also the Maven Question IDs rendered in this code do not reflect the final list of variables HHD 
#--@@@  				want or needs. 	I am still working on that. 
#--@@@  
#--@@@  
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

def custom_logger(message=None):

	logfileDateStamp=DT.datetime.today().strftime('%Y%m%d')
	messageTimeStamp=DT.datetime.today().strftime('%m-%d-%Y %H:%M:%S')

	logfile = open(summaryPath + 'MifBuilder_logfile_v' + logfileDateStamp + '.log','a') 

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

def xml_retrieve_nested(xpathString, xpathString2, attributeName=None): #function to retrieve nested element text or attributes 
	element = root.find(xpathString)									#attribute name is optional, if ommitted it looks for text

	try:
		if not attributeName == None:
			try: 
				item = element.find(xpathString2).get(attributeName)
			except Exception as e:
				item = '--'	
		else:
			item = element.find(xpathString2).text
	
	except Exception as e:
		item = '--'	

	if item == None:
		item = '--'

	return item.replace('\n', ' ').replace('\r', '').replace('\t', ' ').rstrip()

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

	return item.replace('\n', ' ').replace('\r', '').replace('\t', ' ').rstrip()

def xml_retrieve_from_elem(elem, xpathString, attributeName=None):   	#function to retrieve element text or attributes 
	if not attributeName == None:	#attribute name is optional, if ommitted it looks for text
		try:
			item = elem.find(xpathString).get(attributeName)
		except Exception as e:
			item = ''
	else:	
		try:
			item = elem.find(xpathString).text
		except Exception as e:
			item = ''

	if item == None or item == 'None':
		item = ''
	else:
		pass


	return item.replace('\n', ' ').replace('\r', '').replace('\t', ' ').rstrip()

def xml_retrieve_date_fromstring(elem, xpathString, attributeName=None):   	#function to retrieve element text or attributes 
	if not attributeName == None:						#attribute name is optional, if ommitted it looks for text
		try:
			item = DT.datetime.strptime(elem.find(xpathString).get(attributeName)[:8], '%Y%m%d').strftime('%m-%d-%Y')
		except Exception as e:
			item = '--'

	else:	
		try:
			item = DT.datetime.strptime(elem.find(xpathString).text[:8], '%Y%m%d').strftime('%m-%d-%Y')
		except Exception as e:
			item = '--'

	if item == None:
		item = '--'

	return item.replace('\n', ' ').replace('\r', '').replace('\t', ' ').rstrip()

##### Set Vars #####################################################

inputPath 			= '\\python\\projects\\MifBuilder\\CDA_eICR_edge\\'
mIFPath 			= '\\python\\projects\\MifBuilder\\MIF\\' 
cSVPath 			= '\\python\\projects\\MifBuilder\\CSV\\' 
summaryPath 		= '\\python\\projects\\MifBuilder\\logs\\'
mavenInputPath1 	= '\\\\servername\\ecr\\input\\'


fileCounter=0
fileCounterLimit = 200
timestampString=DT.datetime.today().strftime('%Y%m%d%H%M%S')

start_message = 'SCRIPT STARTED'
custom_logger(start_message)

##### Purge folders of any files ###################################

folder_purge(mIFPath)
folder_purge(cSVPath)

##### Crank through the files in a folder ##########################

for root, dirs, files in os.walk(inputPath):  	

	fileCount = len(files)
	filecount_message = 'eICR FILE COUNT: ' + str(fileCount)
	custom_logger(filecount_message)

	if fileCount == 0:
		break

	csvSummaryFilePath = summaryPath + 'ECR_Summary_v'+ timestampString +'.csv'
	csvSummaryHeader = ['col_01', 'col_02', 'col_03', 'col_04', 'col_05', 'col_06', 'col_07', 'col_08', 'col_09', 'col_10', 'col_11', 'col_12', 'col_13']
	csvSummaryFile = open(csvSummaryFilePath, 'w', newline='')
	csvSummaryWriter = csv.writer(csvSummaryFile, delimiter=',')
	csvSummaryWriter.writerow(csvSummaryHeader) 
	print('CSV Summary log is open', '\n')
	openCSVs_message = 'OPEN Summary CSV: ' + csvSummaryFilePath
	custom_logger(openCSVs_message)
	

	for fileName in files: 						# iterate through all files in source folder 
		#if fileName in ('*.ini', '*.xsl'):
		#	continue
		if fileName.endswith(('.ini', '.xsl')):
			continue

		#if fileName == '08953c1a-6e08-496b-8ff1-23bc1ab8b69c_1561502621692.xml':
			#pass
		#else:
			#continue

		if fileCounter >= fileCounterLimit:
			break
		fileCounter+=1								# Limit the number of files it will process
		inputfilePath =	inputPath + fileName	# create a string for the CDA document file name and folder location
		#print(inputfilePath)
		#break
		openECR_message = 'OPEN NEW eIRC: ' + inputfilePath
		custom_logger(openECR_message)

##### Load CDA into xml object tree and parse ######################

		parser = etree.XMLParser(remove_blank_text=True)
		try:
			tree = etree.parse(inputfilePath, parser)
		except Exception as e:
			csvSummaryRow	 = [fileName, str(e) ]
			csvSummaryWriter.writerow(csvSummaryRow) 
			parseMessage = fileName +': tree = etree.parse(inputfilePath, parser) --> '+ str(e) 
			custom_logger(parseMessage)
			continue

		try:
			root = tree.getroot()
		except Exception as e:
			csvSummaryRow	 = [fileName, str(e) ]
			csvSummaryWriter.writerow(csvSummaryRow) 
			getrootMessage = fileName+': root = tree.getroot() --> '+ str(e)
			custom_logger(getrootMessage)
			continue

##### Strip out namespaces in root element #########################
		for elem in root.getiterator():
			if not hasattr(elem.tag, 'find'): 
				csvSummaryRow	 = [fileName]
				csvSummaryWriter.writerow(csvSummaryRow)
				custom_logger(fileName+': strip out namespaces in root element | if not hasattr(elem.tag, find): --> ')
				continue  

			i = elem.tag.find('}')
			if i >= 0:
				elem.tag = elem.tag[i+1:]
		objectify.deannotate(root, cleanup_namespaces=True)

##### Initiate MIF builder #########################################

		MavenIntegrationFormat = etree.Element('MavenIntegrationFormat', GeneratingSystem='Python', DateFormat='MM/dd/yyyy')

##### Set SDTC Namespace ###########################################

		namespace_SDTC = {'s': 'urn:hl7-org:sdtc'}

##### Trigger Codes ################################################

		triggerCode = ''		

		try: 
			triggerCode = root.find('.//component/structuredBody/component/section/entry/act/entryRelationship/observation/value[@s:valueSet="2.16.840.1.114222.4.11.7508"]/translation[@codeSystemName="ICD10"]', namespace_SDTC).get('code')
			triggerLocation = 'Problem List'
		except:
			try:
				triggerCode = root.find('.//component/structuredBody/component/section/entry/act/entryRelationship/observation/value[@s:valueSet="2.16.840.1.114222.4.11.7508"]/translation[@codeSystemName="ICD-10-CM"]', namespace_SDTC).get('code')
				triggerLocation = 'Problem List'
			except:
				try:
					triggerCode = root.find('.//component/structuredBody/component/section/entry/organizer/component/observation/code[@s:valueSet="2.16.840.1.114222.4.11.7508"]', namespace_SDTC).get('code')
					triggerLocation = 'Result List'

				except Exception as e:
					csvSummaryRow	 = [fileName,  str(e) ]
					csvSummaryWriter.writerow(csvSummaryRow) 
					custom_logger(fileName+': triggerCode--> '+ str(e))
					continue



		try: 
			triggerDescription = root.find('.//component/structuredBody/component/section/entry/act/entryRelationship/observation/value[@s:valueSet="2.16.840.1.114222.4.11.7508"]/translation[@codeSystemName="ICD10"]', namespace_SDTC).get('displayName')
		except:
			try:
				triggerDescription = root.find('.//component/structuredBody/component/section/entry/act/entryRelationship/observation/value[@s:valueSet="2.16.840.1.114222.4.11.7508"]/translation[@codeSystemName="ICD-10-CM"]', namespace_SDTC).get('displayName')
			except:
				try:
					triggerDescription = root.find('.//component/structuredBody/component/section/entry/organizer/component/observation/code[@s:valueSet="2.16.840.1.114222.4.11.7508"]/originalText', namespace_SDTC).text
				except:
					try:
						triggerDescription = root.find('.//component/structuredBody/component/section/entry/organizer/component/observation/code[@s:valueSet="2.16.840.1.114222.4.11.7508"]', namespace_SDTC).get('displayName')


					except Exception as e:
						csvSummaryRow	 = [fileName,  str(e) ]
						csvSummaryWriter.writerow(csvSummaryRow) 
						custom_logger(fileName+': triggerDescription--> '+ str(e))
						continue

		#triggerDescription=triggerDescription.replace('\n', ' ').replace('\r', '')

		if triggerCode in ('24111-7', '43305-2','50388-8','57289-1','60256-5', '60255-7', 'A54.01'):
			productCode = 'GONOR'
			continue

		elif triggerCode in ('42931-6','43304-5','47212-6','50387-0','57288-3', '6349-5'):
			productCode = 'CHLAMYDIA'
			continue

		elif triggerCode in ('A02' ,'A02.0' ,'A02.1' ,'A02.2' ,'A02.20' ,'A02.21' ,'A02.22' ,'A02.23' ,'A02.24' ,'A02.25' ,'A02.29' ,'A02.8' ,'A02.9' ,'1092371000119103' ,'127361000119109' ,'186134009' ,'2523007' ,'276288002' ,'302229004' ,'302231008' ,'397503006' ,'402962004' ,'420764009' ,'42338000' ,'449083008' ,'47375003' ,'6803002' ,'71299003' ,'77070006' ,'77645007' ,'90974009','17563-8' ,'20951-0' ,'20952-8' ,'20953-6' ,'20955-1' ,'23431-0' ,'23432-8' ,'23435-1' ,'23436-9' ,'23602-6' ,'34891-2' ,'42255-0' ,'43371-4' ,'48806-4' ,'49612-5' ,'56475-7' ,'59846-6' ,'61370-3' ,'65756-9' ,'73672-8' ,'79383-6'):
			productCode = 'SAL'
			pass

		elif triggerCode in ('80825-3' ,'80826-1' ,'81148-9' ,'81149-7' ,'79190-5' ,'80618-2' ,'80619-0' ,'80823-8' ,'80824-6' ,'80620-8' ,'80621-6' ,'80821-2' ,'80822-0' ,'80622-4' ,'80623-2' ,'80624-0' ,'80625-7','A92.5','11726' ,'3928002' ,'11736'):
			productCode = 'ZIKA'
			continue
			
		elif triggerCode in ('11585-7' ,'16474-9' ,'20992-4' ,'22116-8' ,'22117-6' ,'23826-1' ,'23827-9' ,'23828-7' ,'23829-5' ,'23830-3' ,'23831-1' ,'23832-9' ,'24033-3' ,'24034-1' ,'24035-8' ,'24127-3' ,'24128-1' ,'24129-9' ,'24130-7' ,'25331-0' ,'25332-8' ,'25352-6' ,'25353-4' ,'29657-4' ,'29658-2' ,'29659-0' ,'29672-3' ,'29673-1' ,'29674-9' ,'31266-0' ,'31267-8' ,'31737-0' ,'31998-8' ,'33268-4' ,'34941-5' ,'38198-8' ,'41875-6' ,'41877-2' ,'42328-5' ,'42329-3' ,'42330-1' ,'43360-7' ,'43381-3' ,'43880-4' ,'43881-2' ,'43882-0' ,'43890-3' ,'43891-1' ,'43896-0' ,'43909-1' ,'43913-3' ,'44046-1' ,'44047-9' ,'46253-1' ,'46254-9' ,'48741-3' ,'5059-1' ,'548-8' ,'549-6' ,'550-4' ,'55161-4' ,'62426-2' ,'62428-8' ,'6314-9' ,'6315-6' ,'6316-4' ,'6317-2' ,'63431-1' ,'69366-3' ,'69367-1' ,'69368-9' ,'74765-9' ,'74766-7' ,'78921-4' ,'9362-5' ,'9363-3' ,'9364-1' , '408682005' ,'192650000' ,'27836007' ,'59475000' ,'A37.0' ,'A37.01' ,'A37.00' ,'A37.9' ,'A37.91' ,'A37.90'):
			productCode = 'PERT'
			continue

		elif triggerCode in ('13955-0' ,'48159-8'):
			productCode = 'HEPC'
			continue


		elif triggerCode in ('B34.2', 'B97.29', 'B97.2'): # ICD-10 B34.2 (Coronavirus infection, unspecified) B97.29 (Other coronavirus as the cause of diseases classified elsewhere)
			productCode = 'WUHC'
			outputfilePath = outputPath + 'wuhan\\' + fileName
			copy_file(inputfilePath, outputfilePath)


		else:
			productCode = 'UNK'
			continue

##### Build the CSV document that holds summary data ###############
		csvFilePath = cSVPath + 'ECR_PatientOutput_'+ fileName+'_v'+ timestampString +'.csv'
		csvHeader = ['col_01', 'col_02', 'col_03', 'col_04', 'col_05', 'col_06', 'col_07', 'col_08', 'col_09', 'col_10', 'col_11', 'col_12', 'col_13']
		csvFile = open(csvFilePath, 'w', newline='')
		csvWriter = csv.writer(csvFile, delimiter=',')
		csvWriter.writerow(csvHeader) 
		print('CSV log is open', '\n')
		openCSVf_message = 'OPEN Patient CSV: ' + csvFilePath
		custom_logger(openCSVf_message)

		csvElements = ['fileName: ' + fileName]		

##### Metadata #####################################################

		fileDate = time.strftime('%m-%d-%Y %H:%M:%S',time.localtime(os.path.getmtime(inputfilePath)))

		unid = xml_retrieve('.//id','root')
		versionNumber = xml_retrieve('.//versionNumber','value')
		fileDataIterationStr =  str(int(versionNumber)-1)

		relatedversionType = xml_retrieve('.//relatedDocument', 'typeCode')
		relatedUnid = xml_retrieve('.//relatedDocument/parentDocument/id','root')
		relatedversionNumber = xml_retrieve('.//relatedDocument/parentDocument/versionNumber','value')

		effectiveTime = xml_retrieve('.//effectiveTime','value')[:14]
		effectiveTime = DT.datetime.strptime(effectiveTime, '%Y%m%d%H%M%S').strftime('%m-%d-%Y %H:%M:%S')

		assignedAuthoringDevice = xml_retrieve('.//author/assignedAuthor/assignedAuthoringDevice/manufacturerModelName')


		csvElements.extend(['Device: ' + assignedAuthoringDevice])
		csvElements.extend(['File: ' + fileName])
		csvElements.extend(['File Date: ' + fileDate])
		csvElements.extend(['Time Run: ' + timestampString])
		csvElements.extend(['CDA Timestamp: ' + effectiveTime])
		csvElements.extend(['UNID: ' + unid])
		csvElements.extend(['CDA Version: ' + versionNumber])
		csvElements.extend(['Related UNID: ' + relatedUnid])
		csvElements.extend(['Related CDA Version: ' + relatedversionNumber])
		csvElements.extend(['Trigger Code: ' + triggerCode])
		csvElements.extend(['Trigger Descr: ' + str(triggerDescription)])
		csvElements.extend(['Trigger Location: ' + triggerLocation])
		csvElements.extend(['Product: ' + productCode, ''])



		CaseDefinition = etree.SubElement(MavenIntegrationFormat, 'CaseDefinition', ProductCode=productCode, Status='0', StatusDescription='Open' ,Type='Batch',CustomNumber1='0', CustomNumber2='0' )
		ParticipantDefinition = etree.SubElement(CaseDefinition, 'ParticipantDefinition', Type='Primary', Status='Active')
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=fileDataIterationStr, QuestionID='ECR_FILENAME', Value=fileName)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=fileDataIterationStr, QuestionID='ECR_FILEDATE', Value=fileDate)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=fileDataIterationStr, QuestionID='ECR_TIMESTAMP', Value=effectiveTime)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=fileDataIterationStr, QuestionID='ECR_EHR_NAME', Value=assignedAuthoringDevice)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=fileDataIterationStr, QuestionID='ECR_DOCUMENT_ID', Value=unid)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=fileDataIterationStr, QuestionID='ECR_DOCUMENT_VERSION', Value=versionNumber)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=fileDataIterationStr, QuestionID='ECR_DOCUMENT_ID_RELATED', Value=relatedUnid)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=fileDataIterationStr, QuestionID='ECR_DOCUMENT_VERSION_RELATED', Value=relatedversionNumber)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=fileDataIterationStr, QuestionID='ECR_DOCUMENT_VERSION_RELATED_TYPE', Value=relatedversionType)

		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=fileDataIterationStr, QuestionID='ECR_TRIGGER_LOCATION', Value=triggerLocation)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=fileDataIterationStr, QuestionID='ECR_TRIGGER_CODE', Value=triggerCode)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=fileDataIterationStr, QuestionID='ECR_TRIGGER_CONDITION', Value=str(triggerDescription))

##### Patient ######################################################

		patientFirstName = xml_retrieve('.//recordTarget/patientRole/patient/name/given' )

		patientMiddleName = xml_retrieve('.//recordTarget/patientRole/patient/name/given[2]' )
		if patientMiddleName == '--':
			patientMiddleName = ''

		patientLastName = xml_retrieve('.//recordTarget/patientRole/patient/name/family' )
		patientDOB =  xml_retrieve('.//recordTarget/patientRole/patient/birthTime','value' )

		patientDeceased = root.find('.//recordTarget/patientRole/patient/deceasedInd', namespace_SDTC).get('value')
		if patientDeceased == 'false':
			patientDeceased = 'No'
		elif patientDeceased == 'true':
			try:
				patientDeceased  = DT.datetime.strptime(root.find('.//recordTarget/patientRole/patient/deceasedTime', namespace_SDTC).get('value')[:8], '%Y%m%d').strftime('%m-%d-%Y')
			except Exception as e:
				patientDeceased = 'Yes: Date Unknown'
		else:
			patientDeceased = 'Unknown'





		patientTelecomHome = xml_retrieve('.//recordTarget/patientRole/telecom[@use="HP"]','value')
		patientTelecomMobile = xml_retrieve('.//recordTarget/patientRole/telecom[@use="MC"]','value')
		patientTelecomWork = xml_retrieve('.//recordTarget/patientRole/telecom[@use="WP"]','value')
		patientStreetAddress = xml_retrieve('.//recordTarget/patientRole/addr/streetAddressLine')
		patientCity = xml_retrieve('.//recordTarget/patientRole/addr/city')
		patientState = xml_retrieve('.//recordTarget/patientRole/addr/state')
		patientPostalCode = xml_retrieve('.//recordTarget/patientRole/addr/postalCode')
		patientCounty = xml_retrieve('.//recordTarget/patientRole/addr/county')
		patientCountry = xml_retrieve('.//recordTarget/patientRole/addr/country')
		patientMRN = xml_retrieve('.//recordTarget/patientRole/id[@assigningAuthorityName="EMRN"]','extension')
		patientGender = xml_retrieve('.//recordTarget/patientRole/patient/administrativeGenderCode','displayName' )
		patientMaritalStatus = xml_retrieve('.//recordTarget/patientRole/patient/maritalStatusCode','displayName')
		patientSSN = xml_retrieve('.//recordTarget/patientRole/id[@assigningAuthorityName="Social Security Administration"]','extension')

		patientRace = xml_retrieve('.//recordTarget/patientRole/patient/raceCode','code')
		if patientRace == '1002-5':
			patientRace = 'AMERICAN_INDIAN_ALASKAN_NATIVE'
		elif patientRace == '2028-9':
			patientRace = 'ASIAN'
		elif patientRace == '2054-5':
			patientRace = 'BLACK_AFRICAN_AMERICAN'
		elif patientRace == '2076-8':
			patientRace = 'NATIVE_HAWAIIAN_PACIFIC_ISLANDER'
		elif patientRace == '2106-3':
			patientRace = 'WHITE'
		else:
			patientRace = 'UNKNOWN'

		patientHispanicEthnicity = xml_retrieve('.//recordTarget/patientRole/patient/ethnicGroupCode','code')
		if patientHispanicEthnicity == '2135-2':
			patientHispanicEthnicity = 'YES' 
		elif patientHispanicEthnicity == '2186-5':
			patientHispanicEthnicity = 'NO'
		else:
			patientHispanicEthnicity = 'UNKNOWN'
	
		patientLang = xml_retrieve('.//recordTarget/patientRole/patient/languageCommunication/languageCode', 'code')
		if patientLang == 'afr':
			patientLang = 'Afrikaans'
		elif patientLang == 'amh':
			patientLang = 'Amharic'
		elif patientLang == 'ara':
			patientLang = 'Arabic'
		elif patientLang == 'arm (B)':
			patientLang = 'Armenian'
		elif patientLang == 'bul':
			patientLang = 'Bulgarian'
		elif patientLang == 'cat':
			patientLang = 'Catalan; Valencian'
		elif patientLang == 'cze (B)':
			patientLang = 'Czech'
		elif patientLang == 'che':
			patientLang = 'Chechen'
		elif patientLang == 'chi (B)':
			patientLang = 'Chinese'
		elif patientLang == 'eng':
			patientLang = 'English'
		elif patientLang == 'fil':
			patientLang = 'Filipino'
		elif patientLang == 'fre (B)':
			patientLang = 'French'
		elif patientLang == 'ger (B)':
			patientLang = 'German'
		elif patientLang == 'gre (B)':
			patientLang = 'Greek'
		elif patientLang == 'guj':
			patientLang = 'Gujarati'
		elif patientLang == 'hau':
			patientLang = 'Hausa'
		elif patientLang == 'hin':
			patientLang = 'Hindi'
		elif patientLang == 'hrv':
			patientLang = 'Croatian'
		elif patientLang == 'hun':
			patientLang = 'Hungarian'
		elif patientLang == 'arm (B)':
			patientLang = 'Armenian'
		elif patientLang == 'ind':
			patientLang = 'Indonesian'
		elif patientLang == 'ita':
			patientLang = 'Italian'
		elif patientLang == 'jpn':
			patientLang = 'Japanese'
		elif patientLang == 'kor':
			patientLang = 'Korean'
		elif patientLang == 'kur':
			patientLang = 'Kurdish'
		elif patientLang == 'lao':
			patientLang = 'Lao'
		elif patientLang == 'oji':
			patientLang = 'Ojibwa'
		elif patientLang == 'pan':
			patientLang = 'Punjabi'
		elif patientLang == 'pol':
			patientLang = 'Polish'
		elif patientLang == 'rom':
			patientLang = 'Romany'
		elif patientLang == 'rum (B)':
			patientLang = 'Romanian; Moldavian; Moldovan'
		elif patientLang == 'rus':
			patientLang = 'Russian'
		elif patientLang == 'slo (B)':
			patientLang = 'Slovak'
		elif patientLang == 'slv':
			patientLang = 'Slovenian'
		elif patientLang == 'som':
			patientLang = 'Somali'
		elif patientLang == 'spa':
			patientLang = 'Spanish; Castilian'
		elif patientLang == 'srp':
			patientLang = 'Serbian'
		elif patientLang == 'sun':
			patientLang = 'Sundanese'
		elif patientLang == 'swa':
			patientLang = 'Swahili'
		elif patientLang == 'swe':
			patientLang = 'Swedish'
		elif patientLang == 'tur':
			patientLang = 'Turkish'
		elif patientLang == 'uig':
			patientLang = 'Uighur'
		elif patientLang == 'ukr':
			patientLang = 'Ukrainian'
		elif patientLang == 'vie':
			patientLang = 'Vietnamese'
		elif patientLang == 'yid':
			patientLang = 'Yiddish'
		elif patientLang == 'zap':
			patientLang = 'Zapotec'
		elif patientLang == 'zul':
			patientLang = 'Zulu'
		else:
			pass


		patientEmailElements = root.xpath('.//recordTarget/patientRole/telecom')
		patientEmails = []
		patientEmail = ''
		for patientEmailElement in patientEmailElements:
			if patientEmailElement.get('value')[:6] == 'mailto':
				patientEmails.extend([patientEmailElement.get('value')[7:]])

		try:
			patientEmail = patientEmails[0]
		except:
			pass

##### Deidentification using Faker #################################

		patientRealFirstName = patientFirstName
		patientRealMiddleName = patientMiddleName
		patientRealLastName = patientLastName
		patientRealDOB = patientDOB

		patientRealMRN = patientMRN
		patientRealFullName = patientFirstName + ' ' + patientMiddleName + ' ' +patientLastName 
		patientRealFullAddress = patientStreetAddress + ', ' + patientCity + ', ' +  patientState + ' ' + patientPostalCode

		fake = Faker()
		fake.seed(int(patientMRN)+73952064)	

		patientFirstName = fake.first_name()
		patientMiddleName = fake.first_name()
		patientLastName = fake.last_name()

		csvElements.extend(['Real Name: ' + patientRealFirstName + ' ' + patientRealMiddleName + ' ' +patientRealLastName , ''])

		csvElements.extend(['Fake Name: ' + patientFirstName + ' '  + patientMiddleName + ' ' + patientLastName , ''])
		csvSummaryRow	 = [fileName, unid, patientRealMRN, patientRealFirstName + ' ' + patientRealLastName, patientRealDOB, patientFirstName + ' ' + patientLastName, effectiveTime, versionNumber, relatedversionNumber,triggerCode, triggerDescription, triggerLocation, productCode, patientEmail ]
		csvSummaryWriter.writerow(csvSummaryRow) 


		patientEmail  = fake.email()
		patientStreetAddress = fake.street_address()
		patientCity = fake.city()
		patientState = fake.state_abbr(include_territories=False)
		patientPostalCode = fake.postalcode()
		patientTelecomMobile = fake.phone_number()
		patientTelecomHome = fake.phone_number()
		patientTelecomWork = fake.phone_number()
		patientSSN = fake.ssn(taxpayer_identification_number_type="SSN")
		patientMRN = str(int(patientMRN)+73952064)
		patientDOB = str(fake.date_of_birth())
		patientFullName = patientFirstName + ' '  + patientMiddleName + ' ' + patientLastName
		patientFullAddress = patientStreetAddress + ', ' + patientCity + ', ' +  patientState + ' ' + patientPostalCode

	
		PartyDefinition = etree.SubElement(ParticipantDefinition, 'PartyDefinition', FirstName=patientFirstName, MiddleName=patientMiddleName, LastName=patientLastName,  TaxID=patientSSN, BirthDate=patientDOB,  Type='Case Party', Gender=patientGender, Deidentified='false', Category='Person', ReferenceCategory='-1')
		ContactPointDefinition  = etree.SubElement(PartyDefinition, 'ContactPointDefinition',Type='Home', Street1=patientStreetAddress, PostalCode=patientPostalCode, City=patientCity, State=patientState , County=patientCounty, Country=patientCountry, HomePhone=patientTelecomHome, WorkPhone=patientTelecomWork, MobilePhone=patientTelecomMobile, Email=patientEmail)

		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_PATIENT_NAME', Value=patientFullName)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_PATIENT_ADDRESS', Value=patientFullAddress)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_PATIENT_HOMEPHONE', Value=patientTelecomHome)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_PATIENT_WORKPHONE', Value=patientTelecomWork)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_PATIENT_MOBILEPHONE', Value=patientTelecomMobile)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_PATIENT_EMAIL', Value=patientEmail)

		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_PATIENT_MRN', Value=patientMRN)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_PATIENT_DOB', Value=patientDOB)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_PATIENT_DECEASED', Value=patientDeceased)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_PATIENT_LANGUAGE', Value=patientLang)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_PATIENT_RACE', Value=patientRace)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_PATIENT_ETHNICITY', Value=patientHispanicEthnicity)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='RACE', Value=patientRace)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ETHNICITY', Value=patientHispanicEthnicity)

		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_PATIENT_MARITAL', Value=patientMaritalStatus)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_PATIENT_GENDER', Value=patientGender)

##### Pregnant #####################################################

		pregnancySection = tree.find('.//act/entryRelationship/observation/value[@code="77386006"]') #finds the parent to the <title/> tag

		if not pregnancySection is None:
			pregnancyDisplayName = pregnancySection.find('.//translation').get('displayName')
			pregnancyCode = pregnancySection.find('.//translation').get('code')
			pregnancyCodeSystem = pregnancySection.find('.//translation').get('codeSystem')
			pregnancyCodeSystemName = pregnancySection.find('.//translation').get('codeSystemName')
		else:
			pregnancyCode = 'N/A'
			pregnancyCodeSystem = 'N/A'
			pregnancyCodeSystemName = 'N/A'
			pregnancyDisplayName = 'N/A'
			#print('No Pregnancy Section')

		print(pregnancyCode + ', ' + pregnancyDisplayName)
		csvDataLine = ['Pregnancy Section: '   +  pregnancyDisplayName + ', '+ pregnancyCode + ', ' + pregnancyCodeSystem  + ', '+ pregnancyCodeSystemName ]
		csvWriter.writerow(csvDataLine)

		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_PATIENT_PREGNANCY_DESCR', Value=pregnancyDisplayName)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_PATIENT_PREGNANCY_CODE', Value=pregnancyCode)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_PATIENT_PREGNANCY_CODESYSTEM', Value=pregnancyCodeSystem)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_PATIENT_PREGNANCY_CODESYSTEMNAME', Value=pregnancyCodeSystemName)

##### Guardian #####################################################

		guardianRelationship = xml_retrieve('.//recordTarget/patientRole/patient/guardian/code/originalText')
		guardianFirstName = xml_retrieve('.//recordTarget/patientRole/patient/guardian/guardianPerson/name/given')
		guardianLastName = xml_retrieve('.//recordTarget/patientRole/patient/guardian/guardianPerson/name/family')
		guardianStreetAddress = xml_retrieve('.//recordTarget/patientRole/patient/guardian/addr/streetAddressLine')
		guardianCity = xml_retrieve('.//recordTarget/patientRole/patient/guardian/addr/city')
		guardianState = xml_retrieve('.//recordTarget/patientRole/patient/guardian/addr/state')
		guardianPostalCode = xml_retrieve('.//recordTarget/patientRole/patient/guardian/addr/postalCode')
		guardianTelecomHome = xml_retrieve('.//recordTarget/patientRole/patient/guardian/telecom[@use="HP"]','value')
		guardianTelecomMobile = xml_retrieve('.//recordTarget/patientRole/patient/guardian/telecom[@use="MC"]','value')
		guardianTelecomWork = xml_retrieve('.//recordTarget/patientRole/patient/guardian/telecom[@use="WP"]','value')

		guardianEmailElements = root.xpath('.//recordTarget/patientRole/patient/guardian/telecom')
		guardianEmails = []
		guardianEmail = ''
		for guardianEmailElement in guardianEmailElements:
			if guardianEmailElement.get('value')[:6] == 'mailto':
				guardianEmails.extend([guardianEmailElement.get('value')[7:]])
		try:
			guardianEmail = guardianRealEmail = guardianEmails[0]
		except:
			pass
		
			


		csvElements.extend(['guardianRelationship: ' + guardianRelationship , 'guardianFirstName: ' + guardianFirstName, 'guardianLastName: ' + guardianLastName, 'guardianStreetAddress: ' + guardianStreetAddress, 'guardianCity: ' + guardianCity, 'guardianState: ' + guardianState, 'guardianPostalCode: ' + guardianPostalCode, 'guardianTelecomHome: ' + guardianTelecomHome, 'guardianTelecomMobile: ' + guardianTelecomMobile, 'guardianTelecomWork: ' + guardianTelecomWork, 'guardianEmail: ' + guardianEmail, ''])


		guardianStreetAddress =  fake.street_address()	
		guardianCity =  fake.city()
		guardianState = fake.state_abbr(include_territories=False)
		guardianPostalCode = fake.postalcode()
		guardianTelecomMobile = fake.phone_number()
		guardianTelecomHome = fake.phone_number()
		guardianTelecomWork = fake.phone_number()
		guardianEmail  = fake.email()

		guardianFullName= fake.first_name() + ' ' + fake.last_name()
		guardianAddress =  guardianStreetAddress + ', ' + guardianCity + ', ' + guardianState  + ' ' + guardianPostalCode
		

		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_CONTACT_NAME', Value=guardianFullName)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_CONTACT_RELATIONSHIP', Value=guardianRelationship)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_CONTACT_TYPE', Value='Guardian')
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_CONTACT_ADDRESS', Value=guardianAddress)

		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_CONTACT_HOMEPHONE', Value=guardianTelecomHome)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_CONTACT_WORKPHONE', Value=guardianTelecomWork)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_CONTACT_MOBILEPHONE', Value=guardianTelecomMobile)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_CONTACT_EMAIL', Value=guardianEmail)

##### Participant (Contact) ########################################

		participants = root.xpath('.//participant[@typeCode="IND"]')  #ICD10
		participantCounter = 1
		for participant in participants:



			if participant.find('.//associatedEntity').get('classCode') == "ECON":  
				participantType = 'Emergency Contact'
			elif participant.find('.//associatedEntity').get('classCode') == 'CAREGIVER':
				participantType = 'Caregiver'
			elif participant.find('.//associatedEntity').get('classCode') == 'AGNT':
				participantType = 'Agent'
			elif participant.find('.//associatedEntity').get('classCode') == 'GUAR':
				participantType = 'Guarantor'
			elif participant.find('.//associatedEntity').get('classCode') == 'NOK':
				participantType = 'Next of kin'
			elif participant.find('.//associatedEntity').get('classCode') == 'PRS':
				participantType = 'Personal relationship'
			else:
				participantType = 'Unknown'

			participantRelationship =  xml_retrieve('.//participant/associatedEntity/code/originalText' )
			participantFirstName = xml_retrieve('.//participant/associatedEntity/name/given' )
			participantLastName =xml_retrieve('.//participant/associatedEntity/name/family' )
			participantStreetAddress = xml_retrieve('.//participant/associatedEntity/addr/streetAddressLine')
			participantCity = xml_retrieve('.//participant/associatedEntity/addr/city')
			participantState = xml_retrieve('.//participant/associatedEntity/addr/state')
			participantPostalCode = xml_retrieve('.//participant/associatedEntity/addr/postalCode')
			participantTelecomHome = xml_retrieve('.//participant/associatedEntity/telecom[@use="HP"]','value' )
			participantTelecomMobile = xml_retrieve('.//participant/associatedEntity/telecom[@use="MC"]','value' )
			participantTelecomWork = xml_retrieve('.//participant/associatedEntity/telecom[@use="WP"]','value' )

			participantEmailElements = root.xpath('.//participant/associatedEntity/telecom')
			participantEmails = []
			participantEmail = ''
			for participantEmailElement in participantEmailElements:
				if participantEmailElement.get('value')[:6] == 'mailto':
					participantEmails.extend([participantEmailElement.get('value')[7:]])

			try:
				participantEmail = participantRealEmail = participantEmails[0]
			except:
				pass

			csvElements.extend(['participantRelationship: ' + participantRelationship , 'participantFirstName: ' + participantFirstName, 'participantLastName: ' + participantLastName, 'guardianStreetAddress: ' + participantStreetAddress, 'participantCity: ' + participantCity, 'participantState: ' + participantState, 'participantPostalCode: ' + participantPostalCode, 'participantTelecomHome: ' + participantTelecomHome, 'participantTelecomMobile: ' + participantTelecomMobile, 'participantTelecomWork: ' + participantTelecomWork, 'participantEmail: ' + participantEmail, ''])


			participantStreetAddress =  fake.street_address()	
			participantCity =  fake.city()
			participantState = fake.state_abbr(include_territories=False)
			participantPostalCode = fake.postalcode()
			participantTelecomHome = fake.phone_number()
			participantTelecomMobile = fake.phone_number()
			participantTelecomWork = fake.phone_number()
			participantEmail  = fake.email()

			participantFullName= fake.first_name() + ' ' + fake.last_name()
			participantAddress =  participantStreetAddress + ', ' + participantCity + ', ' + participantState  + ' ' + participantPostalCode

			participantCounterStr= str(participantCounter)

			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=participantCounterStr, QuestionID='ECR_PATIENTCONTACT_NAME', Value=participantFullName )

			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=participantCounterStr, QuestionID='ECR_PATIENTCONTACT_RELATIONSHIP', Value=participantRelationship)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=participantCounterStr, QuestionID='ECR_PATIENTCONTACT_TYPE', Value=participantType)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=participantCounterStr, QuestionID='ECR_PATIENTCONTACT_ADDRESS', Value=participantAddress)

			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=participantCounterStr, QuestionID='ECR_PATIENTCONTACT_HOMEPHONE', Value=participantTelecomHome )
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=participantCounterStr, QuestionID='ECR_PATIENTCONTACT_WORKPHONE', Value=participantTelecomWork)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=participantCounterStr, QuestionID='ECR_PATIENTCONTACT_MOBILEPHONE', Value=participantTelecomMobile)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=participantCounterStr, QuestionID='ECR_PATIENTCONTACT_EMAIL', Value=participantEmail)
			participantCounter += 1

##### Provider Organization ########################################

		providerOrganizationName = xml_retrieve('.//recordTarget/patientRole/providerOrganization/name')
		providerOrganizationStreetAddressLine = xml_retrieve('.//recordTarget/patientRole/providerOrganization/addr/streetAddressLine')
		providerOrganizationCity = xml_retrieve('.//recordTarget/patientRole/providerOrganization/addr/city')
		providerOrganizationState = xml_retrieve('.//recordTarget/patientRole/providerOrganization/addr/state')
		providerOrganizationPostalCode = xml_retrieve('.//recordTarget/patientRole/providerOrganization/addr/postalCode')

		providerOrganizationAddress = providerOrganizationStreetAddressLine + ', ' + providerOrganizationCity + ', ' + providerOrganizationState + ' ' + providerOrganizationPostalCode


		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_PROVIDERORGANIZATION_NAME', Value=providerOrganizationName)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_PROVIDERORGANIZATION_ADDRESS', Value=providerOrganizationAddress)

##### HealthCareFacility ###########################################

		healthCareFacilityName1 = xml_retrieve('.//componentOf/encompassingEncounter/location/healthCareFacility/serviceProviderOrganization/name')
		healthCareFacilityName2 = xml_retrieve('.//componentOf/encompassingEncounter/location/healthCareFacility/location/name')

		healthCareFacilitystreetAddressLine = xml_retrieve('.//componentOf/encompassingEncounter/location/healthCareFacility/location/addr/streetAddressLine')
		healthCareFacilityCity = xml_retrieve('.//componentOf/encompassingEncounter/location/healthCareFacility/location/addr/city')
		healthCareFacilityState = xml_retrieve('.//componentOf/encompassingEncounter/location/healthCareFacility/location/addr/state')		
		healthCareFacilitypostalCode = xml_retrieve('.//componentOf/encompassingEncounter/location/healthCareFacility/location/addr/postalCode')	
		healthCareFacilityCounty = xml_retrieve('.//componentOf/encompassingEncounter/location/healthCareFacility/location/addr/county')	

		healthCareFacilityName = healthCareFacilityName1 + ' AKA ' + healthCareFacilityName2

		healthCareFacilityAddress = healthCareFacilitystreetAddressLine + ', ' + healthCareFacilityCity + ', ' + healthCareFacilityState + ' ' + healthCareFacilitypostalCode + ', ' + healthCareFacilityCounty

		healthCareFacilityPhone = 'To do list'

		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_HEALTHCAREFACILITY_NAME', Value=healthCareFacilityName)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_HEALTHCAREFACILITY_ADDRESS', Value=healthCareFacilityAddress)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_HEALTHCAREFACILITY_PHONE', Value=healthCareFacilityPhone)

##### Care Team ####################################################


		responsiblePartyNameFirst = xml_retrieve('.//componentOf/encompassingEncounter/responsibleParty/assignedEntity/assignedPerson/name/given')
		responsiblePartyNameLast = xml_retrieve('.//componentOf/encompassingEncounter/responsibleParty/assignedEntity/assignedPerson/name/family')

		responsiblePartyNPI = xml_retrieve('.//componentOf/encompassingEncounter/responsibleParty/assignedEntity/id', 'extension')

		responsiblePartystreetAddressLine = xml_retrieve('.//componentOf/encompassingEncounter/responsibleParty/assignedEntity/addr/streetAddressLine')
		responsiblePartyCity = xml_retrieve('.//componentOf/encompassingEncounter/responsibleParty/assignedEntity/addr/city')
		responsiblePartyState = xml_retrieve('.//componentOf/encompassingEncounter/responsibleParty/assignedEntity/addr/state')		
		responsiblePartypostalCode = xml_retrieve('.//componentOf/encompassingEncounter/responsibleParty/assignedEntity/addr/postalCode')	
		responsiblePartyPhone = xml_retrieve('.//componentOf/encompassingEncounter/responsibleParty/assignedEntity/telecom[@use="WP"]','value')
		responsiblePartyFax = xml_retrieve('.//componentOf/encompassingEncounter/responsibleParty/assignedEntity/telecom[2]','value')

		responsiblePartyName = responsiblePartyNameFirst + ' ' + responsiblePartyNameLast

		responsiblePartyAddress = responsiblePartystreetAddressLine + ', ' + responsiblePartyCity + ', ' + responsiblePartyState + ' ' + responsiblePartypostalCode

		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_RESPONSIBLEPARTY_NAME', Value=responsiblePartyName)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_RESPONSIBLEPARTY_NPI', Value=responsiblePartyNPI)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_RESPONSIBLEPARTY_ADDRESS', Value=responsiblePartyAddress)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_RESPONSIBLEPARTY_PHONE', Value=responsiblePartyPhone)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_RESPONSIBLEPARTY_FAX', Value=responsiblePartyFax)



		encompassingEncounter = tree.find('.//componentOf/encompassingEncounter') 
		#print(encompassingEncounter) 
		#exit()
		encounterParticipants = encompassingEncounter.xpath('.//encounterParticipant/assignedEntity')

		#iteratorMultiplier = (int(versionNumber) * 10) - 10
		#encounterParticipantsCounter = iteratorMultiplier
		encounterParticipantsCounter = 0

		for encounterParticipant in encounterParticipants:

			careTeamMemberRole = xml_retrieve_from_elem(encounterParticipant,'.//..', 'typeCode')

			careTeamMemberNameFirst = xml_retrieve_from_elem(encounterParticipant,'.//assignedPerson/name/given')
			careTeamMemberNameLast = xml_retrieve_from_elem(encounterParticipant,'.//assignedPerson/name/family')

			careTeamMemberNPI = xml_retrieve_from_elem(encounterParticipant,'.//id', 'extension')

			careTeamMemberstreetAddressLine = xml_retrieve_from_elem(encounterParticipant,'.//addr/streetAddressLine')
			careTeamMemberCity = xml_retrieve_from_elem(encounterParticipant,'.//addr/city')
			careTeamMemberState = xml_retrieve_from_elem(encounterParticipant,'.//addr/state')		
			careTeamMemberpostalCode = xml_retrieve_from_elem(encounterParticipant,'.//addr/postalCode')	
			careTeamMemberPhone = xml_retrieve_from_elem(encounterParticipant,'.//telecom[@use="WP"]','value')
			careTeamMemberFax = xml_retrieve_from_elem(encounterParticipant,'.//telecom[2]','value')

			careTeamMemberName = careTeamMemberNameFirst + ' ' + careTeamMemberNameLast
			careTeamMemberAddress = careTeamMemberstreetAddressLine + ', ' + careTeamMemberCity + ', ' + careTeamMemberState + ' ' + careTeamMemberpostalCode
			encounterParticipantsCounterStr = str(encounterParticipantsCounter)

			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=encounterParticipantsCounterStr, QuestionID='ECR_CAREGIVER_ROLE', Value=careTeamMemberRole)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=encounterParticipantsCounterStr, QuestionID='ECR_CAREGIVER_NAME', Value=careTeamMemberName)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=encounterParticipantsCounterStr, QuestionID='ECR_CAREGIVER_NPI', Value=careTeamMemberNPI)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=encounterParticipantsCounterStr, QuestionID='ECR_CAREGIVER_ADDRESS', Value=careTeamMemberAddress)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=encounterParticipantsCounterStr, QuestionID='ECR_CAREGIVER_STREET', Value=careTeamMemberstreetAddressLine)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=encounterParticipantsCounterStr, QuestionID='ECR_CAREGIVER_CITY', Value=careTeamMemberCity)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=encounterParticipantsCounterStr, QuestionID='ECR_CAREGIVER_STATE', Value=careTeamMemberState)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=encounterParticipantsCounterStr, QuestionID='ECR_CAREGIVER_ZIP', Value=careTeamMemberpostalCode)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=encounterParticipantsCounterStr, QuestionID='ECR_CAREGIVER_PHONE', Value=careTeamMemberPhone)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=encounterParticipantsCounterStr, QuestionID='ECR_CAREGIVER_FAX', Value=careTeamMemberFax)

			encounterParticipantsCounter += 1

##### Encounter Details ############################################

		encounterSection = tree.find('.//title[.="Encounter Details"]/..') #finds the parent to the <title/> tag

		encountereffectiveDate = encounterSection.find('.//entry/encounter/effectiveTime/low')

		try:
			encountereffectiveDateValue = DT.datetime.strptime(encountereffectiveDate.get('value')[:8], '%Y%m%d').strftime('%m-%d-%Y')
		except Exception as e:
			encountereffectiveDateValue = ''

		encounters = encounterSection.xpath('.//entryRelationship[@typeCode="SUBJ"]/act[@classCode="ACT"]/entryRelationship/observation[@classCode="OBS"]/value/translation[@codeSystem="2.16.840.1.113883.6.90"]')  #ICD10

		#iteratorMultiplier = (int(versionNumber) * 20) - 20 
		#encounterCounter = 0 + iteratorMultiplier
		encounterCounter = 0 

		for encounter in encounters:

			encounterCode = encounter.get('code')
			encounterdisplayName = encounter.get('displayName')
			encounterCounterStr = str(encounterCounter)
			print('Encounter Details:', encountereffectiveDateValue, '', encounterCode, encounterdisplayName )
			csvDataLine = ['Encounter Details:',  encountereffectiveDateValue, '',encounterCode, encounterdisplayName , encounterCounterStr ]
			csvWriter.writerow(csvDataLine)

			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=encounterCounterStr, QuestionID='ECR_ENCOUNTER_DATE', Value=encountereffectiveDateValue)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=encounterCounterStr, QuestionID='ECR_ENCOUNTER_CODE', Value=encounterCode)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=encounterCounterStr, QuestionID='ECR_ENCOUNTER_NAME', Value=encounterdisplayName)

			encounterCounter += 1

		csvWriter.writerow('')

##### Setting and Reason for Visit #################################

		settingDateStart = xml_retrieve('.//componentOf/encompassingEncounter/effectiveTime/low', 'value')[:12]
		try:
			settingDateStart = DT.datetime.strptime(settingDateStart, '%Y%m%d%H%M%S').strftime('%m-%d-%Y %H:%M:%S')
		except Exception as e:
			settingDateStart = ''

		settingDateEnd = xml_retrieve('.//componentOf/encompassingEncounter/effectiveTime/high', 'value')[:12]
		try:
			settingDateEnd = DT.datetime.strptime(settingDateEnd, '%Y%m%d%H%M%S').strftime('%m-%d-%Y %H:%M:%S')
		except Exception as e:
			settingDateEnd = ''


		setting = xml_retrieve('.//componentOf/encompassingEncounter/code/originalText')
		reasonText = xml_retrieve_nested('.//title[.="Reason for Visit"]/..','.//entry/observation/value/originalText')

		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=fileDataIterationStr, QuestionID='ECR_VISIT_DATE_START', Value=settingDateStart)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=fileDataIterationStr, QuestionID='ECR_VISIT_DATE_END', Value=settingDateEnd)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=fileDataIterationStr, QuestionID='ECR_VISIT_SETTING', Value=setting)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=fileDataIterationStr, QuestionID='ECR_REASON_FOR_VISIT', Value=reasonText)

		csvElements.extend(['setting: ' + setting  + ', ' + settingDateStart  + ', ' + reasonText]) # Write first part to CSV file
		for csvElement in csvElements:  
			print(csvElement)
			csvElementList = [csvElement]
			csvWriter.writerow(csvElementList)

##### Problems #####################################################

		problemSection = tree.find('.//title[.="Problems"]/..') #finds the parent to the <title/> tag

		problems = problemSection.xpath('.//entry/act[@classCode="ACT"]')

		#iteratorMultiplier = (int(versionNumber) * 100) - 100 
		#problemCounter = 0 + iteratorMultiplier
		problemCounter = 0 

		for problem in problems:


			problemDateStart = xml_retrieve_date_fromstring(problem,'.//entryRelationship/observation/effectiveTime/low','value') #ECR_PROBLEM_DATE_START
			problemDateStop = xml_retrieve_date_fromstring(problem,'.//entryRelationship/observation/effectiveTime/high','value') #
			problemDescription = xml_retrieve_from_elem(problem,'.//entryRelationship/observation/value/translation','displayName')
			problemCode = xml_retrieve_from_elem(problem,'.//entryRelationship/observation/value/translation','code')
			problemCodeSystem = xml_retrieve_from_elem(problem,'.//entryRelationship/observation/value/translation','codeSystem')
			problemCodeSystemName = xml_retrieve_from_elem(problem,'.//entryRelationship/observation/value/translation','codeSystemName')


			problemIterationStr =  str(int(problemCounter))

			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=problemIterationStr, QuestionID='ECR_PROBLEM_DATE_START', Value=problemDateStart)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=problemIterationStr, QuestionID='ECR_PROBLEM_DATE_STOP', Value=problemDateStop)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=problemIterationStr, QuestionID='ECR_PROBLEM_DESCR', Value=problemDescription)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=problemIterationStr, QuestionID='ECR_PROBLEM_CODE', Value=problemCode)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=problemIterationStr, QuestionID='ECR_PROBLEM_CODESYSTEM', Value=problemCodeSystem)			
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=problemIterationStr, QuestionID='ECR_PROBLEM_CODESYSTEMNAME', Value=problemCodeSystemName)

			problemCounter += 1

			print(         'Problem: ',  problemDateStart, problemDateStop, problemDescription, problemCode, problemCodeSystem, problemCodeSystemName )
			csvDataLine = ['Problem: ',  problemDateStart, problemDateStop, problemDescription, problemCode, problemCodeSystem, problemCodeSystemName ]
			csvWriter.writerow(csvDataLine)



		csvWriter.writerow('')

##### Admitting Diagnosis ##########################################

		admittingDiagnosisCode = xml_retrieve('.//component/structuredBody/component/section/code[@code="46241-6"]/entry/act/entryRelationship/observation/value/translation[@codeSystem="2.16.840.1.113883.6.90"]', 'code') 

		admittingDiagnosisdisplayName = xml_retrieve('.//component/structuredBody/component/section/code[@code="46241-6"]/entry/act/entryRelationship/observation/value/translation[@codeSystem="2.16.840.1.113883.6.90"]', 'displayName')

		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_ADMITTINGDX_CODE', Value=admittingDiagnosisCode)
		RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration='0', QuestionID='ECR_ADMITTINGDX_DESCR', Value=admittingDiagnosisdisplayName)

##### Visit Diagnosis ##############################################



		visitdxSection = tree.find('.//title[.="Visit Diagnoses"]/..') #finds the parent to the <title/> tag

		#iteratorMultiplier = (int(versionNumber) * 20) - 20 
		#iterCounter = 0 + iteratorMultiplier
		iterCounter = 0 

		if not visitdxSection is None:
			dxTables = visitdxSection.xpath('.//text/table/tbody/tr')
			if not dxTables is None:
				for i, dxTable in enumerate(dxTables):

					tableparagraphContent = dxTable.find('.//td/paragraph/content')
					tableparagraph2Content = dxTable.find('.//td/paragraph[2]')
					if not tableparagraph2Content is None:
						tableparagraph2ContentStr = tableparagraph2Content.text
					else:
						tableparagraph2ContentStr = 'No Further Description'
					if i==0:
						primarydxLabel = 'Primary - '	
					else:
						primarydxLabel = 'Secondary - '
					diagnosis = primarydxLabel + tableparagraphContent.text + ' (' + tableparagraph2ContentStr + ')'
					print('Visit Diagnoses:',  primarydxLabel + tableparagraphContent.text + ' (' + tableparagraph2ContentStr + ')')
					csvDataLine = ['Visit Diagnoses:', primarydxLabel + tableparagraphContent.text + ' (' + tableparagraph2ContentStr + ')']
					csvWriter.writerow(csvDataLine)
					iterString = str(iterCounter)

					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=iterString, QuestionID='ECR_VISIT_DIAGNOSIS_DESCR_DEPRECATED', Value=diagnosis)
					iterCounter +=1
			else: 
				print('Visit Diagnoses:',  'None')
				csvDataLine = ['Visit Diagnoses:',  'None']
				csvWriter.writerow(csvDataLine)
		else: 
			print('Visit Diagnoses:',   'None')
			csvDataLine = ['Visit Diagnoses:',  'None']
			csvWriter.writerow(csvDataLine)
		csvWriter.writerow('')

##### Results ######################################################

		result = tree.find('.//title[.="Results"]/..') #finds the parent to the <title/> tag
		
	#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@	
	#BATTERIES (REGULAR DIAGNOSTIC TESTS)

		batteries = result.xpath('.//entry[@typeCode="DRIV"]/organizer[@classCode="BATTERY"]')

		#iteratorMultiplier = (int(versionNumber) * 500) - 500
		#batteryCounter = iteratorMultiplier
		batteryCounter = 0

		for battery in batteries:
			if not xml_retrieve_from_elem(battery,'.//specimen/specimenRole/specimenPlayingEntity/code/translation','displayName') == ' ':
				batSpecimen = xml_retrieve_from_elem(battery,'.//specimen/specimenRole/specimenPlayingEntity/code/translation','displayName')
				batSpecimenLocation = 'batSpecimenLocation1'
			elif not xml_retrieve_from_elem(battery,'.//specimen/specimenRole/specimenPlayingEntity/code/originalText') == ' ':
				batSpecimen = xml_retrieve_from_elem(battery,'.//specimen/specimenRole/specimenPlayingEntity/code/originalText')
				batSpecimenLocation = 'batSpecimenLocation2'
			elif not xml_retrieve_from_elem(battery,'.//component/procedure/participant/participantRole/playingEntity/code/originalText') == ' ':
				batSpecimen = xml_retrieve_from_elem(battery,'.//component/procedure/participant/participantRole/playingEntity/code/originalText')
				batSpecimenLocation = 'batSpecimenLocation3'
			else:
				batSpecimen = 'No Specimen Found'
				batSpecimenLocation = 'batSpecimenLocation4'

			batDate = xml_retrieve_date_fromstring(battery,'.//effectiveTime/low','value')
			batName = xml_retrieve_from_elem(battery,'.//code/originalText')
			batCode = xml_retrieve_from_elem(battery,'.//code', 'code')
			batPerformer = str.title(xml_retrieve_from_elem(battery,'.//performer/assignedEntity/representedOrganization/name')) + ': ' + xml_retrieve_from_elem(battery,'.//performer/assignedEntity/representedOrganization/addr/streetAddressLine') + ', ' + xml_retrieve_from_elem(battery,'.//performer/assignedEntity/representedOrganization/addr/city')  + ', ' + xml_retrieve_from_elem(battery,'.//performer/assignedEntity/representedOrganization/addr/state')  + ' ' + xml_retrieve_from_elem(battery,'.//performer/assignedEntity/representedOrganization/addr/postalCode')  + ', ' + xml_retrieve_from_elem(battery,'.//performer/assignedEntity/representedOrganization/telecom', 'value') 

			batObservations = battery.xpath('.//component/observation[@classCode="OBS"]')

			for batObservation in batObservations:			

				obsDate = xml_retrieve_date_fromstring(batObservation,'.//effectiveTime','value')
				obsCode = xml_retrieve_from_elem(batObservation,'.//code', 'code')
				obsOrigText = xml_retrieve_from_elem(batObservation,'.//code/originalText')


				obsValue = xml_retrieve_from_elem(batObservation,'.//value', 'value') + ' ' + xml_retrieve_from_elem(batObservation,'.//value', 'unit') + xml_retrieve_from_elem(batObservation,'.//value') + ' '	+ xml_retrieve_from_elem(batObservation,'.//interpretationCode/originalText')


				obsreferenceRange = xml_retrieve_from_elem(batObservation,'.//referenceRange/observationRange/text')

				resultNameCombined = batName + ': ' + obsOrigText



				batteryCounterStr = str(batteryCounter)

				print(         'Test Panel:', batteryCounterStr, batName, batCode, batSpecimen, batSpecimenLocation, batDate, obsCode, obsOrigText, obsValue, obsreferenceRange, batPerformer)
				csvDataLine = ['Test Panel:', batteryCounterStr, batName, batCode, batSpecimen, batSpecimenLocation, batDate, obsCode, obsOrigText, obsValue, obsreferenceRange, batPerformer]
				csvWriter.writerow(csvDataLine)

				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=batteryCounterStr, QuestionID='ECR_RESULTS_PANELDATE', Value=batDate)
				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=batteryCounterStr, QuestionID='ECR_RESULTS_SPECIMEN', Value=batSpecimen)
				#RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=batteryCounterStr, QuestionID='ECR_RESULTS_PANELNAME', Value=batName)
				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=batteryCounterStr, QuestionID='ECR_RESULTS_PANELCODE', Value=batCode)
				#RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=batteryCounterStr, QuestionID='ECR_RESULTS_TESTNAME', Value=obsOrigText)
				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=batteryCounterStr, QuestionID='ECR_RESULTS_TESTNAME', Value=resultNameCombined)

				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=batteryCounterStr, QuestionID='ECR_RESULTS_TESTCODE', Value=obsCode)
				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=batteryCounterStr, QuestionID='ECR_RESULTS_TESTRESULTDATE', Value=obsDate)

				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=batteryCounterStr, QuestionID='ECR_RESULTS_TESTRESULT', Value=obsValue)
				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=batteryCounterStr, QuestionID='ECR_RESULTS_TESTRESULT_REFRANGE', Value=obsreferenceRange)
				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=batteryCounterStr, QuestionID='ECR_RESULTS_LAB', Value=batPerformer)

				batteryCounter += 1

	#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
	#CLUSTERS (MICROBIOLOGY ONLY)

		clusters = result.xpath('.//entry[@typeCode="DRIV"]/organizer[@classCode="CLUSTER"]')

		iteratorMultiplier = (int(versionNumber) * 50) - 50
		clusterCounter = iteratorMultiplier

		for cluster in clusters:

			clusterCounterStr = str(clusterCounter)

			#CLUSTER META 
			clusterCode = xml_retrieve_from_elem(cluster,'.//code', 'code')#	CLUSTER NAME
			clusterName = xml_retrieve_from_elem(cluster,'.//code/originalText')#	CLUSTER NAME
			clusterPerformer =  str.title(xml_retrieve_from_elem(cluster,'.//performer/assignedEntity/representedOrganization/name')) + ': ' + xml_retrieve_from_elem(cluster,'.//performer/assignedEntity/representedOrganization/addr/streetAddressLine') + ', ' + xml_retrieve_from_elem(cluster,'.//performer/assignedEntity/representedOrganization/addr/city')  + ', ' + xml_retrieve_from_elem(cluster,'.//performer/assignedEntity/representedOrganization/addr/state')  + ' ' + xml_retrieve_from_elem(cluster,'.//performer/assignedEntity/representedOrganization/addr/postalCode') + ', ' + xml_retrieve_from_elem(cluster,'.//performer/assignedEntity/representedOrganization/telecom', 'value') 



			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=clusterCounterStr, QuestionID='ECR_MICRO_TESTCODE', Value=clusterCode)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=clusterCounterStr, QuestionID='ECR_MICRO_TESTNAME', Value=clusterName)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=clusterCounterStr, QuestionID='ECR_MICRO_LAB', Value=clusterPerformer)

		#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@	
		#CLUSTER COMPONENT (SPECIMEN) /component/procedure/participant/participantRole/playingEntity/code/originalText	


			if not xml_retrieve_from_elem(cluster,'.//component/procedure[@classCode="PROC"][@moodCode="EVN"]/participant/participantRole/playingEntity/code/originalText') == '':
				clusterspecimen =  xml_retrieve_from_elem(cluster,'.//component/procedure[@classCode="PROC"][@moodCode="EVN"]/participant/participantRole/playingEntity/code/originalText')
				clusterSpecimenLocation = 'clusterSpecimenLocation1'

			elif not xml_retrieve_from_elem(cluster,'.//specimen/specimenRole/specimenPlayingEntity/code/translation', 'displayName') == '':
				clusterspecimen =  xml_retrieve_from_elem(cluster,'.//specimen/specimenRole/specimenPlayingEntity/code/translation', 'displayName')
				clusterSpecimenLocation = 'clusterSpecimenLocation2'
			else:
				clusterspecimen =  'No Cluster Specimen Found'
				clusterSpecimenLocation = 'clusterSpecimenLocation3'

			if not xml_retrieve_date_fromstring(cluster, './/component/procedure/effectiveTime', 'value') == '--':
				clusterspecimenDate = xml_retrieve_date_fromstring(cluster, './/component/procedure/effectiveTime', 'value')
			elif not xml_retrieve_date_fromstring(cluster, './/effectiveTime/low', 'value')  == '--':
				clusterspecimenDate = xml_retrieve_date_fromstring(cluster, './/effectiveTime/low', 'value')
			else:
				clusterspecimenDate = 'No Cluster Specimen Date'

			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=clusterCounterStr, QuestionID='ECR_MICRO_SPECIMEN', Value=clusterspecimen)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=clusterCounterStr, QuestionID='ECR_MICRO_SPECIMENDATE', Value=clusterspecimenDate)

			print(         'Cluster: ', clusterCounterStr, clusterName, clusterspecimen, clusterSpecimenLocation, clusterPerformer)
			csvDataLine = ['Cluster: ', clusterCounterStr, clusterName, clusterspecimen, clusterSpecimenLocation, clusterPerformer]
			csvWriter.writerow(csvDataLine)
		#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@	
		#CLUSTER COMPONENT (INTERPRETATION) //component/observation/code[@code="56850-1"]/../value
			
			interpretation = xml_retrieve_from_elem(cluster,'.//component/observation/code[@code="56850-1"]/../value')
			interpretationDate = xml_retrieve_date_fromstring(cluster, './/component/observation/code[@code="56850-1"]/../effectiveTime','value')

			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=clusterCounterStr, QuestionID='ECR_MICRO_INTERPRETATION', Value=interpretation)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=clusterCounterStr, QuestionID='ECR_MICRO_INTERPRETATIONDATE', Value=interpretationDate)

		#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@	
		#CLUSTER COMPONENT (Result) 

			clusterResult = cluster.find('.//component[@typeCode="COMP"]/organizer[@classCode="BATTERY"][@moodCode="EVN"]')
			clusterResultStr = xml_retrieve_from_elem(clusterResult,'.//code/originalText')
			clusterResultDate = xml_retrieve_date_fromstring(clusterResult, './/effectiveTime/low', 'value')

			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=clusterCounterStr, QuestionID='ECR_MICRO_RESULT', Value=clusterResultStr)
			RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=clusterCounterStr, QuestionID='ECR_MICRO_RESULTDATE', Value=clusterResultDate)





			clusterCounter += 1				
		#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@	
		#CLUSTER COMPONENT (Susceptibilities) 

			susceptibilities = clusterResult.xpath('.//component/observation[@classCode="OBS"][@moodCode="EVN"]')


			for susceptibility in susceptibilities:



				susceptDate = xml_retrieve_date_fromstring(susceptibility, './/effectiveTime', 'value')
				susceptCode = xml_retrieve_from_elem(susceptibility,'.//code','code')

				susceptTest = xml_retrieve_from_elem(susceptibility,'.//code/originalText')
				susceptTest = '.  ' + susceptTest.replace('\n', '').replace('\t', '').replace('\r', '')

				susceptMethod = xml_retrieve_from_elem(susceptibility,'.//methodCode/originalText')
				susceptResult = xml_retrieve_from_elem(susceptibility,'.//value') #>&lt;=2 mcg/mL: Susceptible
				susceptResult = '.  ' + susceptMethod + ': ' + susceptResult.replace('\n', '').replace('\t', '').replace('\r', '')

				clusterCounterStr = str(clusterCounter)

				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=clusterCounterStr, QuestionID='ECR_MICRO_SPECIMENDATE', Value=clusterspecimenDate)

				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=clusterCounterStr, QuestionID='ECR_MICRO_SPECIMEN', Value=clusterspecimen)


				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=clusterCounterStr, QuestionID='ECR_MICRO_TESTNAME', Value=susceptTest)
				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=clusterCounterStr, QuestionID='ECR_MICRO_TESTCODE', Value=susceptCode)


				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=clusterCounterStr, QuestionID='ECR_MICRO_RESULTDATE', Value=susceptDate)
				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=clusterCounterStr, QuestionID='ECR_MICRO_RESULT', Value=susceptResult)
				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=clusterCounterStr, QuestionID='ECR_MICRO_INTERPRETATION', Value='placeholder')

				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=clusterCounterStr, QuestionID='ECR_MICRO_LAB', Value=clusterPerformer)

				clusterCounter += 1				


		csvWriter.writerow('')

##### Social History ###############################################

		tabSection = tree.find('.//title[.="Social History"]/..') #finds the parent to the <title/> tag

		#iteratorMultiplier = (int(versionNumber) * 50) - 50
		#socialCounter= 0 + iteratorMultiplier
		socialCounter = 0 

		if not tabSection is None:

			tabTables = tabSection.xpath('.//text/table')

			print(len(tabTables), str(socialCounter))
			
			for tabTable in tabTables:

				tableHeads = tabTable.xpath('.//thead/tr/th')
				tableBodyTrs = tabTable.xpath('.//tbody/tr')
				for tableBodyTr in tableBodyTrs:
					tableBodyTds = tableBodyTr.xpath('.//td')
					tableContentLine = ''

					for x in range(int(len(tableHeads))):
						try:
							if not tableBodyTds[x].text is None:
								tableBodyTdsxTextStr = tableBodyTds[x].text
							else:
								tableBodyTdsxTextStr = '-'
							
							tableContentLine = tableContentLine + tableHeads[x].text + ': "' + tableBodyTdsxTextStr + '" '
						except Exception as e:
							pass	
					socialCounterString = str(socialCounter)

					print(         'Social History :', socialCounterString, tableContentLine)
					csvDataLine = ['Social History :', socialCounterString, tableContentLine]
					csvWriter.writerow(csvDataLine)

					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=socialCounterString, QuestionID='ECR_SOCIAL_HISTORY', Value=tableContentLine)
					socialCounter += 1


		else:
			print(		   'Social History:',  'No History Listed')
			csvDataLine = ['Social History:',  'No History Listed']
			csvWriter.writerow(csvDataLine)

		csvWriter.writerow('')

##### Procedures ###################################################

		procedureSection = tree.find('.//title[.="Procedures"]/..') #finds the parent to the <title/> tag
		#iteratorMultiplier = (int(versionNumber) * 50) - 50
		#procedureCounter= iteratorMultiplier		
		procedureCounter= 0
		try:
			procedures = procedureSection.xpath('.//entry/procedure')

			for procedure in procedures:

				procedureCodeSystemName = xml_retrieve_from_elem(procedure,'.//code','codeSystemName')
				procedureCode = xml_retrieve_from_elem(procedure,'.//code','code')
				procedureeffectiveTime = xml_retrieve_date_fromstring(procedure, './/effectiveTime', 'value')
				procedureoriginalText = xml_retrieve_from_elem(procedure,'.//code/originalText')
				procedureReason = xml_retrieve_from_elem(procedure,'.//entryRelationship[@typeCode="RSON"]/observation/text')

				csvDataLine = ['Procedures: ', procedureeffectiveTime, procedureCodeSystemName, procedureCode, procedureoriginalText, procedureReason ]
				csvWriter.writerow(csvDataLine)
				
				procedureCounterString = str(procedureCounter)

				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=procedureCounterString, QuestionID='ECR_PROCEDURE_DATE', Value=procedureeffectiveTime)
				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=procedureCounterString, QuestionID='ECR_PROCEDURE_CODE_SYSTEM', Value=procedureCodeSystemName)
				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=procedureCounterString, QuestionID='ECR_PROCEDURE_CODE', Value=procedureCode)
				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=procedureCounterString, QuestionID='ECR_PROCEDURE_DESCRIPTION', Value=procedureoriginalText)
				RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=procedureCounterString, QuestionID='ECR_PROCEDURE_REASON', Value=procedureReason)

				procedureCounter += 1
			csvWriter.writerow('')
		except Exception as e:
			csvWriter.writerow([str(e)+ '\tNo Procedures'])

##### Plan of Treatment  deprecated ############################################

		planSection = tree.find('.//title[.="Plan of Treatment"]/..') #finds the parent to the <title/> tag
		#iteratorMultiplier = (int(versionNumber) * 50) - 50
		#planCounter = iteratorMultiplier
		planCounter = 0

		if not planSection is None:

			planTables = planSection.xpath('.//text/table')
			
			for planTable in planTables:
				tableCaption = planTable.find('.//caption')
				tableHeads = planTable.xpath('.//thead/tr/th')
				tableBodyTrs = planTable.xpath('.//tbody/tr')
				
				for tableBodyTr in tableBodyTrs:
					tableBodyTds = tableBodyTr.xpath('.//td')
					tableContentLine = ''
					for x in range(int(len(tableHeads))):
						if not tableBodyTds[x].text is None:
							tableBodyTdsxTextStr = tableBodyTds[x].text
						else:
							tableBodyTdsxTextStr = '---'
						
						tableContentLine = tableContentLine + tableHeads[x].text + ': ' + tableBodyTdsxTextStr + ';   '

					csvDataLine = ['Plan of Treatment: ' + tableContentLine ]

					csvWriter.writerow(csvDataLine)
				
					planCounterString = str(planCounter)

					#RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=planCounterString, QuestionID='ECR_PLAN_OF_TREATMENT', Value=tableContentLine)

					planCounter += 1


		else:
			csvDataLine = ['Plan of Treatment: No Plan Listed']
			csvWriter.writerow(csvDataLine)

##### Plan of Treatment ##################################################


		planOfTxSection = tree.find('.//title[.="Plan of Treatment"]/..') #finds the parent to the <title/> tag

		planCounter = 0

		#custom_logger('plan Section started ----------------------------------')

		plans = planOfTxSection.xpath('.//entry')

		try:
			#custom_logger('plan Section trying ----------------------------------')

			if not planOfTxSection is None:
				#custom_logger('plan Section if notting ----------------------------------')
				for plan in plans:
					#custom_logger('plan Section foring ----------------------------------')

					planDate = xml_retrieve_date_fromstring(plan,'.//encounter/effectiveTime/low','value') #ECR_PLAN_OF_TREATMENT_DATE
					planDescription = xml_retrieve_from_elem(plan,'.//observation/code','displayName') #ECR_PLAN_OF_TREATMENT_DESCR
					planCode = xml_retrieve_from_elem(plan,'.//observation/code','code')  #ECR_PLAN_OF_TREATMENT_CODE
					planCodeSystem = xml_retrieve_from_elem(plan,'.//observation/code','codeSystem')  #ECR_PLAN_OF_TREATMENT_CODESYSTEM
					planCodeSystemName = xml_retrieve_from_elem(plan,'.//observation/code','codeSystemName')  #ECR_PLAN_OF_TREATMENT_CODESYSTEMNAME

					planStatus = xml_retrieve_from_elem(plan,'.//observation/statusCode', 'code')  #ECR_PLAN_OF_TREATMENT_STATUS
					planCarePerson = xml_retrieve_from_elem(plan,'.//encounter/performer/assignedEntity/assignedPerson/name')  #ECR_PLAN_OF_TREATMENT_CAREPERSON
					planCarePersonAddress =  xml_retrieve_from_elem(plan,'.//encounter/participant/participantRole/addr/streetAddressLine') + ', ' + xml_retrieve_from_elem(plan,'.//encounter/participant/participantRole/addr/city')  + ', ' + xml_retrieve_from_elem(plan,'.//encounter/participant/participantRole/addr/state')  + ' ' + xml_retrieve_from_elem(plan,'.//encounter/participant/participantRole/addr/postalCode')  #ECR_PLAN_OF_TREATMENT_CAREPERSON_ADDRESS

					planCarePersonPhone = xml_retrieve_from_elem(plan,'.//encounter/performer/assignedEntity/[@use="WP"]','value')  #ECR_PLAN_OF_TREATMENT_CAREPERSON_PHONE
					planCarePersonFax = xml_retrieve_from_elem(plan,'.//encounter/performer/assignedEntity/telecom[2]','value')  #ECR_PLAN_OF_TREATMENT_CAREPERSON_FAX
					#custom_logger('plan Section no difficulting retrieving xml ----------------------------------')

					planCounterStr =  str(int(planCounter))

					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=planCounterStr, QuestionID='ECR_PLAN_OF_TREATMENT_DATE', Value=planDate)
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=planCounterStr, QuestionID='ECR_PLAN_OF_TREATMENT_DESCR', Value=planDescription)
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=planCounterStr, QuestionID='ECR_PLAN_OF_TREATMENT_CODE', Value=planCode)
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=planCounterStr, QuestionID='ECR_PLAN_OF_TREATMENT_CODESYSTEM', Value=planCodeSystem)
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=planCounterStr, QuestionID='ECR_PLAN_OF_TREATMENT_CODESYSTEMNAME', Value=planCodeSystemName)
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=planCounterStr, QuestionID='ECR_PLAN_OF_TREATMENT_STATUS', Value=planStatus)
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=planCounterStr, QuestionID='ECR_PLAN_OF_TREATMENT_CAREPERSON', Value=planCarePerson)
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=planCounterStr, QuestionID='ECR_PLAN_OF_TREATMENT_CAREPERSON_ADDRESS', Value=planCarePersonAddress)
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=planCounterStr, QuestionID='ECR_PLAN_OF_TREATMENT_CAREPERSON_PHONE', Value=planCarePersonPhone)
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=planCounterStr, QuestionID='ECR_PLAN_OF_TREATMENT_CAREPERSON_FAX', Value=planCarePersonFax)

					#custom_logger('plan Section no difficulting miffing ----------------------------------')

					planCounter += 1

					#custom_logger('plan Section no difficulting counting ----------------------------------')

			else:
				pass
		except Exception as e:
			custom_logger('plan Section error' + ' ' +str(e))
			pass		

		csvWriter.writerow('')

##### Medications ##################################################

		#iteratorMultiplier = (int(versionNumber) * 100) - 100 
		#medicationCounter = 0 + iteratorMultiplier
		medicationCounter = 0 

		medicationSection = tree.find('.//templateId[@root="2.16.840.1.113883.10.20.22.2.38"]/..') #finds the parent to the <title/> tag
		#medicationSection = tree.find('.//title[.="Administered Medications"]/..') #finds the parent to the <title/> tag

		medications = medicationSection.xpath('.//entry/substanceAdministration[@classCode="SBADM"]')

		try:
			if not medicationSection is None:
				for medication in medications:

					medicationStartDate = xml_retrieve_date_fromstring(medication,'.//effectiveTime/low','value') #ECR_MEDICATION_DATESTART
					medicationStopDate = xml_retrieve_date_fromstring(medication,'.//effectiveTime/high','value') #ECR_MEDICATION_DATESTOP
					medicationName = xml_retrieve_from_elem(medication,'.//consumable/manufacturedProduct/manufacturedMaterial/code/originalText') + xml_retrieve_from_elem(medication,'.//consumable/manufacturedProduct/manufacturedMaterial/code/translation', 'displayName')  #ECR_MEDICATION_NAME
					if medicationName.strip() == '':
						continue
					medicationCode = xml_retrieve_from_elem(medication,'.//consumable/manufacturedProduct/manufacturedMaterial/code','code')  #ECR_MEDICATION_CODE
					medicationCodeSystem = xml_retrieve_from_elem(medication,'.//consumable/manufacturedProduct/manufacturedMaterial/code','codeSystem')  #ECR_MEDICATION_CODESYSTEM
					medicationCodeSystemName = xml_retrieve_from_elem(medication,'.//consumable/manufacturedProduct/manufacturedMaterial/code','codeSystemName')  #ECR_MEDICATION_CODESYSTEMNAME
					medicationdoseQuantity = xml_retrieve_from_elem(medication,'.//doseQuantity','value') + xml_retrieve_from_elem(medication,'.//doseQuantity','unit') #ECR_MEDICATION_DOSE
					medicationRoute = xml_retrieve_from_elem(medication,'.//routeCode','displayName') #ECR_MEDICATION_ROUTE
					medicationStatus = xml_retrieve_from_elem(medication,'.//statusCode', 'code')  #ECR_MEDICATION_STATUS

					medicationCounterStr =  str(int(medicationCounter))

					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=medicationCounterStr, QuestionID='ECR_MEDICATION_DATE_START', Value=medicationStartDate)
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=medicationCounterStr, QuestionID='ECR_MEDICATION_DATE_STOP', Value=medicationStopDate)
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=medicationCounterStr, QuestionID='ECR_MEDICATION_NAME', Value=medicationName)
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=medicationCounterStr, QuestionID='ECR_MEDICATION_CODE', Value=medicationCode)
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=medicationCounterStr, QuestionID='ECR_MEDICATION_CODESYSTEM', Value=medicationCodeSystem)
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=medicationCounterStr, QuestionID='ECR_MEDICATION_CODESYSTEMNAME', Value=medicationCodeSystemName)
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=medicationCounterStr, QuestionID='ECR_MEDICATION_DOSE', Value=medicationdoseQuantity)
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=medicationCounterStr, QuestionID='ECR_MEDICATION_ROUTE', Value=medicationRoute)
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=medicationCounterStr, QuestionID='ECR_MEDICATION_STATUS', Value=medicationStatus)

					medicationCounter += 1


			else:
				pass
		except Exception as e:
			custom_logger('medication Section error' + ' ' +str(e))
			pass		

		csvWriter.writerow('')

##### Allergies Placeholder ########################################

##### Vital Signs Placeholder ######################################

##### Travel Placeholder ###########################################

##### SexAtBirth Placeholder #######################################

##### Immunizations ################################################
		immunizationsSection = tree.find('.//title[.="Immunizations"]/..') #finds the parent to the <title/> tag

		#immunizationsSection = tree.find('.//templateId[@root="2.16.840.1.113883.10.20.22.2.2"]/..') #finds the parent to the <title/> tag
		immunizationsCounter = 0 
		#print('Immunizations Start')
		#custom_logger('immunizationsSection1' + ' ' +str(immunizationsSection))
		try:				

			if not immunizationsSection is None:
				immunizations = immunizationsSection.xpath('.//entry')

				for immunization in immunizations:
					
					immunizationDate = xml_retrieve_date_fromstring(immunization,'.//substanceAdministration/effectiveTime','value') #ECR_IMMUNIZATION_DATE
					immunizationDisplayName = xml_retrieve_from_elem(immunization,'.//substanceAdministration/consumable/manufacturedProduct/manufacturedMaterial/code/translation','displayName') #ECR_IMMUNIZATION_NAME
					immunizationCode = xml_retrieve_from_elem(immunization,'.//substanceAdministration/consumable/manufacturedProduct/manufacturedMaterial/code/translation','code') #ECR_IMMUNIZATION_CODE
					immunizationCodeSystem = xml_retrieve_from_elem(immunization,'.//substanceAdministration/consumable/manufacturedProduct/manufacturedMaterial/code/translation','codeSystem')  #ECR_IMMUNIZATION_CODESYSTEM
					immunizationCodeSystemName = xml_retrieve_from_elem(immunization,'.//substanceAdministration/consumable/manufacturedProduct/manufacturedMaterial/code/translation','codeSystemName')  #ECR_IMMUNIZATION_CODESYSTEMNAME
					immunizationMood = xml_retrieve_from_elem(immunization,'.//substanceAdministration','moodCode')  #ECR_IMMUNIZATION_MOOD
					immunizationStatus = xml_retrieve_from_elem(immunization,'.//substanceAdministration/statusCode','code')  #ECR_IMMUNIZATION_STATUS


					immunizationRouteCode = xml_retrieve_from_elem(immunization,'.//substanceAdministration/routeCode','code') #ECR_IMMUNIZATION_ROUTE_CODE
					immunizationRouteDescr = xml_retrieve_from_elem(immunization,'.//substanceAdministration/routeCode','displayName') #ECR_IMMUNIZATION_ROUTE_DESCR
					immunizationDoseQuantity = xml_retrieve_from_elem(immunization,'.//substanceAdministration/doseQuantity','value') + ' ' + xml_retrieve_from_elem(immunization,'.//substanceAdministration/doseQuantity','unit') #ECR_IMMUNIZATION_DOSE
					immunizationLotNumber = xml_retrieve_from_elem(immunization,'.//substanceAdministration/consumable/manufacturedProduct/manufacturedMaterial/lotNumberText')  #ECR_IMMUNIZATION_LOT
					immunizationManufacturerOrganization = xml_retrieve_from_elem(immunization,'.//substanceAdministration/consumable/manufacturedProduct/manufacturerOrganization/name')  #ECR_IMMUNIZATION_MANUFACTURER

					immunizationPerformer = xml_retrieve_from_elem(immunization,'.//substanceAdministration/performer/name')  #ECR_IMMUNIZATION_PERFORMER
					immunizationPerformerAddress = xml_retrieve_from_elem(immunization,'.//substanceAdministration/performer/addr')  #ECR_IMMUNIZATION_PERFORMER_ADDRESS
					immunizationPerformerPhone = xml_retrieve_from_elem(immunization,'.//substanceAdministration/performer/tel')  #ECR_IMMUNIZATION_PERFORMER_PHONE
		

					immunizationsCounterStr = str(immunizationsCounter)

					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=immunizationsCounterStr, QuestionID='ECR_IMMUNIZATION_DATE', Value=immunizationDate)
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=immunizationsCounterStr, QuestionID='ECR_IMMUNIZATION_NAME', Value=immunizationDisplayName )
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=immunizationsCounterStr, QuestionID='ECR_IMMUNIZATION_CODE', Value=immunizationCode )
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=immunizationsCounterStr, QuestionID='ECR_IMMUNIZATION_CODESYSTEM', Value=immunizationCodeSystem )
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=immunizationsCounterStr, QuestionID='ECR_IMMUNIZATION_CODESYSTEMNAME', Value=immunizationCodeSystemName )
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=immunizationsCounterStr, QuestionID='ECR_IMMUNIZATION_MOOD', Value=immunizationMood )
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=immunizationsCounterStr, QuestionID='ECR_IMMUNIZATION_STATUS', Value=immunizationStatus )
					
					#RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=immunizationsCounterStr, QuestionID='ECR_IMMUNIZATION_NEXTDUE', Value='to do' )

					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=immunizationsCounterStr, QuestionID='ECR_IMMUNIZATION_ROUTE_CODE', Value=immunizationRouteCode )
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=immunizationsCounterStr, QuestionID='ECR_IMMUNIZATION_ROUTE_DESCR', Value=immunizationRouteDescr )
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=immunizationsCounterStr, QuestionID='ECR_IMMUNIZATION_DOSE', Value=immunizationDoseQuantity )
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=immunizationsCounterStr, QuestionID='ECR_IMMUNIZATION_LOT', Value= immunizationLotNumber)
					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=immunizationsCounterStr, QuestionID='ECR_IMMUNIZATION_MANUFACTURER', Value=immunizationManufacturerOrganization )

					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=immunizationsCounterStr, QuestionID='ECR_IMMUNIZATION_PERFORMER', Value=immunizationPerformer )

					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=immunizationsCounterStr, QuestionID='ECR_IMMUNIZATION_PERFORMER_ADDRESS', Value=immunizationPerformerAddress )

					RiskDataDefinition = etree.SubElement(ParticipantDefinition, 'RiskDataDefinition', Iteration=immunizationsCounterStr, QuestionID='ECR_IMMUNIZATION_PERFORMER_PHONE', Value=immunizationPerformerPhone )





					immunizationsCounter +=1

			else:
				pass
		except Exception as e:
			custom_logger('immunizationsSection error' + ' ' +str(e))
			pass		
					
##### Close patient CSV file #######################################
		csvFile.close()	

		closeCSVf_message = 'CLOSE Patient CSV: ' + csvFilePath
		custom_logger(closeCSVf_message)

##### Write the MIF file ###########################################

		xmlObject = etree.tostring(MavenIntegrationFormat).decode()
		xmlReparsed = MD.parseString(xmlObject)
		xmlIndented = xmlReparsed.toprettyxml(indent='\t')

		outputfilePath = mIFPath + fileName + '_v' + timestampString + '.xml'    #create new filename for pretty xml
		outputfilePathContents = open(outputfilePath, 'w') 

		try: 
		    print(xmlIndented, file = outputfilePathContents)  
		except Exception as e:
		    print('\t', fileName, '\n', '\t', e)
		    #exit()

		outputfilePathContents.close()
		writeMIF_message = 'WRITE MIF: ' + outputfilePath
		custom_logger(writeMIF_message)

##### Close summary CSV file #######################################

	csvSummaryFile.close()	
	closeCSVs_message = 'CLOSE Summary CSV: ' + csvSummaryFilePath
	custom_logger(closeCSVs_message)
	print('')

##### Copy MIFs to ingestion folder ################################

copy_or_move_files_to_folder(mIFPath, mavenInputPath1, 'COPY')

end_message = '\nSCRIPT ENDED\n'
print(end_message)
custom_logger(end_message)


##### End of script#################################################

