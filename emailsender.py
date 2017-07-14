#!/usr/bin/env python

import os
import smtplib
import mimetypes
import argparse
from email.mime.multipart import MIMEMultipart
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText

# Argument Parser
parser = argparse.ArgumentParser(description='Process inputs', formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=55))
parser.add_argument("-s", "--sender", metavar="<sender>", type=str, default="pythonscript@labs.test", help="def: pythonscript@labs.test")
parser.add_argument("-r", "--recipient", metavar="<recipient>", type=str, required=True)
parser.add_argument("-m", "--mta", metavar="<ip address>", type=str, required=True, help="IP address of next-hop MTA")
parser.add_argument("-p", "--port", metavar="<port>", type=str, help="Port email will send on (def: 25)", default="25")
parser.add_argument("-a", "--attach", metavar="<attachment>", type=str, nargs='+', help="Full or relative path to attachment")
parser.add_argument("-S", "--subject", metavar="<subject>", type=str, help="Subject of the email", default="email sent by python script")

# Mutually exclusive group for body types (you can use a string or a file, not both)
body_group = parser.add_mutually_exclusive_group()
body_group.add_argument("-b", "--body", metavar="<body>", type=str, help="String for the body of the email")
# body_group.add_argument("-B", "--body", metavar="<body>", type=str, help="Full or relative path to email body file")

parser.add_argument("-H", action="store_true", help="Adds an HTML body in addition to the plain text body")
parser.add_argument("-t", action="store_true", help="Enable TLS")
parser.add_argument("-q", action="store_true", help="Attempts to get a queue id, but may have unexpected results")
parser.add_argument("-v", action="store_true", help="Verbose mode")

args = parser.parse_args()

# Creates key/value pair to return qids and filenames
qids = {}

def main():
	# Build the SMTP Connection
	server = buildsmtp()

	# Iterate through, building and sending messages for each attachment provided	
	for a in args.attach:
		msg = buildmsg(a)	
		qid = sendmsg(server, msg)
		qids[qid] = a

	# Close SMTP connection	
	prquit = server.docmd("QUIT")
	
	if (args.v):
		print prquit 

	# Debugging
	#for x in qids:
	#	print x, qids[x]	

	return qids


def buildsmtp():
	# Create the SMTP object (server format "ip:port") Note: This actually checks to see if the port is open
	try: 
		server = smtplib.SMTP(args.mta + ":" + args.port)
	except:
		print "Error 001: Unable to connect to " + args.mta + " on port " + args.port
		exit()	
	
	# If selected, attempts to negotiate TLS (also, prhelo = print helo)
	if args.t:
		prhelo = server.ehlo()
		try:
			server.starttls()
			server.ehlo()
			if args.v:
				print "TlS started successfully."
		except: 
			print "TLS was not accepted by " + args.mta + ". \nAttempting to send unencrypted."
	
	# If no TLS flag, initiates the connection
	else:
		try:
			prhelo = server.docmd("helo", "labs.test")
		except:
			print "Error 002: Sending email failed, could be a bad address?" 
	if args.v:
		print "Attempting to send the email to " + args.mta + ":" + args.port
	
	if args.v:
		print prhelo
	
	# NOT YET IMPLEMENTED
	# This can be used for server auth (like gmail), but it's disabled. You will need to add the 'server.login(username,password)' line in somewhere
	# username = "user"
	# password = "password"
	# server.login(username,password)
	return server


def buildmsg(a):
	# Create the message and add sender, recipient and subject (This will be used if you aren't using the -q flag)
	msg = MIMEMultipart()
	msg["From"] = args.sender
	msg["To"] = args.recipient
	msg["Subject"] = args.subject
	msg.preamble = args.subject
	
	# Create the alternative for the text/plain and text/html. This object is attached inside the multipart message
	alt_msg = MIMEMultipart('alternative')
	
	# Verbose logging to display to/from/subj
	if args.v:
		print "\n### Verbose Output Enabled ###\n"
		print "From: " + args.sender
		print "To: " + args.recipient
		print "Subject: " + args.subject 
		if a:
			print "Attachment:  " + os.path.basename(a) + "\n"
	
	# Attaches text/plain. Also attaches HTML if it is selected
	# https://docs.python.org/3/library/email-examples.html (RFC 2046)
	alt_msg.attach(MIMEText(args.body, "plain"))
	if args.H:
		alt_msg.attach(MIMEText(args.body, "html"))
	
	msg.attach(alt_msg)
	
	# Checks for an attachment argument, and if there is one identify it's type. 
	# Borrowed from https://docs.python.org/2.4/lib/node597.html
	if a is not None:
		ctype, encoding = mimetypes.guess_type(a)
		if ctype is None or encoding is not None:
		    ctype = "application/octet-stream"
		
		maintype, subtype = ctype.split("/", 1)
		
		if maintype == "text":
		    fp = open(a)
		    # Note: we should handle calculating the charset
		    attachment = MIMEText(fp.read(), _subtype=subtype)
		    fp.close()
		elif maintype == "image":
		    fp = open(a, "rb")
		    attachment = MIMEImage(fp.read(), _subtype=subtype)
		    fp.close()
		elif maintype == "audio":
		    fp = open(a, "rb")
		    attachment = MIMEAudio(fp.read(), _subtype=subtype)
		    fp.close()
		else:
		    fp = open(a, "rb")
		    attachment = MIMEBase(maintype, subtype)
		    attachment.set_payload(fp.read())
		    fp.close()
		    encoders.encode_base64(attachment)
		attachment.add_header("Content-Disposition", "attachment", filename=os.path.basename(a))
		msg.attach(attachment)
	
	# This line will literally print the entire email including headers
	# print "\n\n\n" + msg.as_string() + "\n\n\n"

	return msg

def sendmsg(server, msg):
	# Sends the email DATA
	prfrom = server.docmd("MAIL from:", args.sender)
	prto = server.docmd("RCPT to:", args.recipient)
	prdata = server.docmd("DATA")
	qidline = server.docmd(msg.as_string() + "\r\n.")
	
	
	# Prints what happened above when attempting to send
	if args.v:
		print prfrom
		print prto
		print prdata
		print qidline

	qid = qidline[1].split(" ")[4]
	if args.q:
		print qid
	return qid


if __name__== "__main__":
  main()
