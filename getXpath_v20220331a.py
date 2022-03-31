# Enter xml file path where it says xmlFile = '....xml' on line 31 and execute script

import xml.etree.ElementTree as ET



def parseXML(root,xpathString):

	xpathString = xpathString + "/" + root.tag[root.tag.rfind('}')+1:]
	for child in root:
		if not child.text:
			if not child.attrib:
				parseXML(child,xpathString)
			else: 
				parseXML(child,xpathString)
				childAttrib_Dict = child.attrib
				for key in childAttrib_Dict:
					print('\t'	+ '@' +str(key) +'="'	+str(childAttrib_Dict[key]) +'"')
		else: 
			parseXML(child,xpathString)
			childText = child.text.replace('\t','').replace('\n','')
			if childText == '':
				pass
			else:	
				print('\t'  + childText.replace('  ','').replace('   ','').replace('    ','').replace('    ','') )

	if len(list(root)) == 0:
		print('\n'+xpathString.replace('\t','') )


xmlFile = 'C:/xmlFolder/myXmlFile.xml'

xmlObject = ET.parse(xmlFile).getroot()

parseXML(xmlObject,'')

print('\nEnd of script\n')




