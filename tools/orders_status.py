#!/usr/bin/env python3

import sys, subprocess, os
import fhutils

from dateutil.relativedelta import *
import dateutil
import getopt
from datetime import datetime, time
from dateutil import tz, parser

import email, smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import chardet

subject_line = """ FH:%s Errors found in Submitted Orders """


error_msg ="""
The orders which were submitted for your Species have been found to contain
errors.  Please look over the LOG file that is attached and correct any 
mistakes.

If you need assistance with an error, first consult the game manual.  If 
that does not give clarity for the error(s) listed, visit the MeWe site and
ask there for general help.

Be careful with how you phrase your question(s) as you may give away your
evil plans! bwuhahahahaha
"""

def main(argv):
    global server, port,ssl
    global message,deadline_msg, start_msg
    #config = fhutils.GameConfig()
    #data_dir = os.getcwd() # Adding the ability to call from the game's directory
    email = "No"
    config_file = None
    test_flag = False
    species_num = None
    try:
        opts, args = getopt.getopt(argv, "hc:ts:se:", ["help", "config=","test","species","subject","email"])
    except getopt.GetoptError:
        print(__doc__)
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        elif opt in ("-c", "--config"):
            config_file = arg
        elif opt in ("-t", "--test"):
            test_flag = True
        elif opt in ("-s", "--species"):
            species_num = arg
        elif opt in ("-u", "--subject"):
            subject = arg
        elif opt in ("-e", "--email"):
            email = arg
        else:
            assert False, "unhandled option"
            
    if config_file:
        config = fhutils.GameConfig(config_file)
    else:
        config = fhutils.GameConfig()
    game = config.gameslist[0] # for now we only support a single game
    game_name = game['name']
    game_stub = game['stub']
    deadline_rule = game['deadline']
    data_dir = game['datadir']
    bin_dir = config.bindir
    players = fhutils.Game().players
    sender_address = config.user
    sender_pass = config.password
    try:
       game = fhutils.Game()
    except IOError:
        print("Could not read fh_names")
        sys.exit(2)
    
    if not os.path.isdir(data_dir):
        print("Sorry data directory %s does not exist." % (data_dir))
        sys.exit(2)
    longest_name = len(max([x['name'] for x in game.players], key=len))
    for player in game.players:
        name = player['name'].center(longest_name)
        orders = "%s/sp%s.ord" %(data_dir, player['num'])
        logging = "sp%s.ord.log" %(player['num'])
        #logfile = open(logging, 'w')

        try:
            with open(orders, "r+") as f:
                #print(type(f))
                test = f.read()
                test = test.encode("UTF-8")
                #print(type(test))
                msg = error_msg
                p = subprocess.Popen(["/usr/bin/perl", "/home/jason/Far-Horizons/bash/orders.pl"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
                subprocess.call(["/usr/bin/perl /home/jason/Far-Horizons/bash/orders.pl < %s > %s" %(orders, logging) ],stdin=True, stdout=True, stderr=True, shell=True)
                #test = test.encode('utf-8')
                verify = p.communicate(input=test)[0]
                #print(chardet.detect(verify))
                #print(verify)
                verify = verify.decode('utf-8')
                #print(type(verify))
                if "No errors found" in verify:
                    print("%s - %s - Ready" %(player['num'], name))
                else:
                    if("No" in email):
                        print("%s - %s - Errors" %(player['num'], name))
                    else:
                        print("%s - %s - Errors ----> Emailing!" %(player['num'], name))
                        receiver_address = player['email']
                        #Setup the MIME
                        message = MIMEMultipart()
                        message['From'] = sender_address
                        message['To'] = receiver_address
                        message['Subject'] = (subject_line %(game_stub))   #The subject line
                        #The body and the attachments for the mail
                        message.attach(MIMEText(msg, 'plain'))
                        attach_file_name = logging  # "sp%s.zip" % player['num']
                        with open(logging,'rb') as file:
                            # Attach the file with filename to the email
                            message.attach(MIMEApplication(file.read(), Name=attach_file_name))

                        session = smtplib.SMTP('smtp.gmail.com', 587) #use gmail with port
                        session.starttls() #enable security
                        session.login(sender_address, sender_pass) #login with mail_id and password
                        text = message.as_string()
                        session.sendmail(sender_address, receiver_address, text)
                        session.quit()
                
        except IOError:
            print("%s - %s - No Orders" %(player['num'], name))
                
if __name__ == "__main__":
    main(sys.argv[1:])
