#!/usr/bin/env python3

import sys, subprocess, os, codecs
from imapclient import IMAPClient
import email, email.utils, email.parser, pyzmail, smtplib, ssl
import fhutils, base64
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.mime.base import MIMEBase

server = "imap.gmail.com"
port = 993
ssl = True

VeriText = """This email is to verify that the GM has received and downloaded your orders for this deadline.  Please verify that the orders are correct!"""

# Function to get email content part i.e its body part
def get_body(msg):
    if msg.is_multipart():
        return get_body(msg.get_payload(0))
    else:
        return msg.get_payload(None, True)
  
# Function to search for a key value pair 
def search(key, value, con): 
    result, data = con.search(None, key, '"{}"'.format(value))
    return data
  
# Function to get the list of emails under this label
def get_emails(result_bytes):
    msgs = [] # all the email data are pushed inside an array
    for num in result_bytes[0].split():
        typ, data = con.fetch(num, '(RFC822)')
        msgs.append(data)
  
    return msgs
    
def main():
    global server, port,ssl
    config = fhutils.GameConfig()
    # Adding the ability to run the commands from a directory without having
    # to hard code that directory into the python file.
    data_dir = os.getcwd()
    game_stub = config.gameslist[0]['stub']
    try:
       game = fhutils.Game()
    except IOError:
        print("Could not read fh_names")
        sys.exit(2)
    
    if not os.path.isdir(data_dir):
        print("Sorry data directory %s does not exist." % (data_dir))
        sys.exit(2)
    user_name = config.user
    user_pass = config.password
    msg = VeriText
    seen_unread = []
    unread_list = []
    #server = imaplib.IMAP4_SSL(server)
    server = IMAPClient('imap.gmail.com', ssl=True)
    #IMAPClient(server, use_uid=True, ssl=ssl)
    server.login(user_name, user_pass)
    select_info = server.select_folder('INBOX',readonly=True)
    unread_list = server.search(['UNSEEN'])

    # Parsing the emails
    for unread in unread_list:
        rawMessages = server.fetch([unread],[b'BODY[]', 'FLAGS'])
        #message = 
        mail = pyzmail.PyzMessage.factory(rawMessages[unread][b'BODY[]'])
        subject = mail.get_subject()
        #mail = message.message_from_string(message[k])
        addressor = mail.get("From")
        from_address = email.utils.parseaddr(addressor)[1]
        if 'wait' in mail.get_subject():
            wait = True
        else:
            wait = False
        for player in game.players:
            if from_address == player['email']:
                print("Player Found and Processing : %s" % from_address)
                orders_file = "%s/sp%s.ord" %(data_dir, player['num'])
                fd = codecs.open(orders_file, 'w', 'utf-8')
                orders = None
                if mail.is_multipart():
                    print("Multipart Message detected, searching for plain text payload!")
                    for part in mail.walk():
                        # multipart/* are just containers
                        if part.get_content_maintype() == 'multipart':
                            continue
                        filename = part.get_filename()
                        if not filename:
                            continue
                        if part.get_content_type() != "text/plain":
                            print("Error: attachment found, but not a plain text file for "  + from_address)
                        else:
                            print("found orders in attachment")
                            orders = part.get_payload(decode=True)
                    if orders is None: # ok, no attachment, lets try the actual content
                        payloads = mail.get_payload()
                        try:
                            found = False
                            for loads in payloads:
                                if loads.get_content_type()  == "text/plain":
                                    mail = loads
                                    found = True
                                    print("found orders in multipart payload")
                                    orders = loads.get_payload(decode=True)
                                    break
                            if not found:
                                raise email.errors.MessageError
                        except email.errors.MessageError:
                            print("Could not find text/plain payload for " + from_address)
                else:
                    print("using orders in plain body")
                    orders = mail.get_payload(decode=True).decode('utf-8')
                orders = orders.decode('utf-8')
                orders = orders.replace('\r\n', '\n').replace('\r', '\n')
#	.decode('UTF-8')
#                orders = str(orders, 'utf-8')
                orders = orders.replace("\u00A0", " ").encode('utf-8')
                orders = orders.decode('utf-8')
                fd.write(orders)
                fd.close()
                config = fhutils.GameConfig()
                game = config.gameslist[0] # for now we only support a single game
                game_name = game['name']
                game_stub = game['stub']
                data_dir = game['datadir']
                bin_dir = config.bindir

                orders = orders.encode('utf-8')
                p = subprocess.Popen(["/usr/bin/perl", "/home/jason/Far-Horizons/bash/orders.pl"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
                verify = p.communicate(input=orders)[0]
                subject = "FH Orders, %s Verified Receipt" % (game_stub)
                message = MIMEMultipart()
                message['From'] = user_name
                message['To'] = from_address
                message['Subject'] = subject #The subject line
                #The body and the attachments for the mail
                message.attach(MIMEText(msg, 'plain'))
                with open(orders_file,'rb') as file:
                    # Attach the file with filename to the email
                    message.attach(MIMEApplication(file.read(), Name=orders_file))
                text = message.as_string()
                session = smtplib.SMTP('smtp.gmail.com', 587) #use gmail with port
                session.starttls() #enable security
                session.login(user_name, user_pass) #login with mail_id and pass
                session.sendmail(user_name, from_address, text)
                session.quit()
            #    server.login(user_name, user_pass)
#                mailisread = pyzmail.PyzMessage.factory(rawMessages[unread][b'BODY[]'])
                server.select_folder('Inbox')
                msg_data = server.fetch([unread],[b'BODY[]'])
#                config.send_mail(subject, from_address, verify, orders_file)
                print("Retrieved orders %s for sp%s - %s - %s" %("[WAIT]" if wait else "", player['num'], player['name'], from_address))
                
if __name__ == "__main__":
    main()
