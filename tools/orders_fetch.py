#!/usr/bin/env python

import sys, subprocess, os, codecs
from imapclient import IMAPClient
import email, email.utils, email.parser, imaplib
import fhutils

server = "imap.gmail.com"
port = 993
ssl = True

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
    data_dir = config.gameslist[0]['datadir']  #only support one game now
    game_stub = config.gameslist[0]['stub']
    try:
       game = fhutils.Game()
    except IOError:
        print("Could not read fh_names")
        sys.exit(2)
    
    if not os.path.isdir(data_dir):
        print("Sorry data directory %s does not exist." % (data_dir))
        sys.exit(2)
    
    user_name = "email@address.com"
    user_pass = "SomePassword"
    
    server = imaplib.IMAP4_SSL(server)
    #IMAPClient(server, use_uid=True, ssl=ssl)
    server.login(user_name, user_pass)
    select_info = server.select('INBOX')
    print(select_info)
    messages = get_emails(search('UNSEEN', 'SUBJECT "FH Orders"', server)
    print(messages)
    for k in messages:
        mail = email.message_from_string(messages[k]'(RFC822)')
        addressor = mail.get("From")
        from_address = email.utils.parseaddr(addressor)[1]
        if 'wait' in mail.get("Subject"):
            wait = True
        else:
            wait = False
        for player in game.players:
            if from_address == player['email']:
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
                    orders = mail.get_payload(decode=True)
                orders = orders.replace('\r\n', '\n').replace('\r', '\n')
                orders = str(orders, 'utf-8')
                orders = orders.replace("\u00A0", " ").encode('utf-8')
                fd.write(orders)
                fd.close()
                p = subprocess.Popen(["/usr/bin/perl", "/home/userdir/Far-Horizons/src/fh/engine/bash/orders.pl"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
                verify = p.communicate(input=orders)[0]
                subject = "FH Orders, %s received" % (game_stub)
                if wait:
                    subject += " - wait set"
                else:
                    subject += " - wait not set"
                config.send_mail(subject, from_address, verify, orders_file)
                print("Retrieved orders %s for sp%s - %s - %s" %("[WAIT]" if wait else "", player['num'], player['name'], from_address))
                
if __name__ == "__main__":
    main()
