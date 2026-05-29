#!/usr/bin/env python3

import sys, subprocess, os, shutil
from imapclient import IMAPClient
import email, email.utils, email.parser, smtplib, ssl
import fhutils, base64
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.mime.base import MIMEBase

try:
    import pyzmail36 as pyzmail
except ImportError:
    import pyzmail

server = "imap.gmail.com"
port = 993
ssl = True

VeriText = """This email is to verify that the GM has received and downloaded your orders for this deadline.  Please verify that the orders are correct!"""


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def verifier_script_path():
    return os.path.join(repo_root(), "bash", "orders.pl")


def windows_to_wsl_path(path):
    normalized = os.path.abspath(path).replace("\\", "/")
    drive, tail = os.path.splitdrive(normalized)
    if drive:
        return "/mnt/%s%s" % (drive[0].lower(), tail)
    return normalized


def verifier_command():
    script_path = verifier_script_path()
    if not os.path.isfile(script_path):
        raise FileNotFoundError("Could not find orders verifier script: %s" % script_path)

    perl_path = shutil.which("perl")
    if perl_path:
        return [perl_path, script_path]

    if os.name == "nt" and shutil.which("wsl.exe"):
        return ["wsl.exe", "perl", windows_to_wsl_path(script_path)]

    raise FileNotFoundError(
        "Could not find a Perl runtime. Install Perl or enable WSL to run %s" % script_path
    )


def verify_orders(orders_bytes):
    completed = subprocess.run(
        verifier_command(),
        input=orders_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0 and completed.stderr:
        print("orders.pl verification warning: %s" % completed.stderr.decode("utf-8", errors="replace").strip())
    return completed.stdout


def decode_part_text(part):
    payload = part.get_payload(decode=True)
    if payload is None:
        payload = part.get_payload()
        if isinstance(payload, str):
            return payload
        return None
    if isinstance(payload, str):
        return payload
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset)
    except (LookupError, UnicodeDecodeError):
        return payload.decode("utf-8", errors="replace")


def extract_orders_text(mail, from_address):
    if not mail.is_multipart():
        print("using orders in plain body")
        return decode_part_text(mail)

    print("Multipart Message detected, searching for plain text payload!")
    text_attachment = None
    text_body = None
    fallback_attachment = None
    for part in mail.walk():
        if part.get_content_maintype() == 'multipart':
            continue
        payload_text = decode_part_text(part)
        if not payload_text:
            continue
        filename = (part.get_filename() or "").lower()
        content_type = part.get_content_type()
        disposition = (part.get_content_disposition() or "").lower()
        is_attachment = disposition == "attachment" or bool(filename)
        if content_type == "text/plain":
            if is_attachment:
                print("found orders in text attachment")
                return payload_text
            if text_body is None:
                text_body = payload_text
                print("found orders in multipart payload")
        elif filename.endswith((".ord", ".txt")):
            fallback_attachment = payload_text
    if fallback_attachment is not None:
        print("found orders in text-like attachment")
        return fallback_attachment
    if text_body is not None:
        return text_body
    print("Could not find text/plain payload for " + from_address)
    return None

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
                orders = extract_orders_text(mail, from_address)
                if orders is None:
                    print("Skipping message with no usable order text for %s" % from_address)
                    continue
                orders = orders.replace('\r\n', '\n').replace('\r', '\n')
#	.decode('UTF-8')
#                orders = str(orders, 'utf-8')
                orders = orders.replace("\u00A0", " ").encode('utf-8')
                orders = orders.decode('utf-8')
                with open(orders_file, 'w', encoding='utf-8') as fd:
                    fd.write(orders)
                config = fhutils.GameConfig()
                game = config.gameslist[0] # for now we only support a single game
                game_name = game['name']
                game_stub = game['stub']
                data_dir = game['datadir']
                bin_dir = config.bindir

                orders = orders.encode('utf-8')
                verify = verify_orders(orders)
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
