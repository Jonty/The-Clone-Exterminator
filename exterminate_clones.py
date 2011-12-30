import sys
import imaplib
import getpass
import md5
import re
from collections import defaultdict

# This is a shit way to gather options.
c = imaplib.IMAP4(raw_input('Server: '))
c.login(raw_input('User: '), getpass.getpass())
mailbox = raw_input('Mailbox: ')

seen_messages = {}
duplicate_messages = defaultdict(set)

try:
    c.select(mailbox)

    typ, [data] = c.search(None, 'ALL')
    msg_ids = data.split()

    # We chunk the fetch because some mailservers throw a fit if you request
    # too much data at once
    chunk_size = 1000
    msg_id_chunks = [
        msg_ids[x:x + chunk_size] for x in xrange(0, len(msg_ids), chunk_size)
    ]

    messages = []
    for chunk in msg_id_chunks:
        print '\rFetching messages %s to %s...' % (chunk[0], chunk[-1]),
        sys.stdout.flush()

        typ, data = c.fetch(
            ','.join(chunk),
            '(BODY.PEEK[HEADER.FIELDS (TO FROM SUBJECT DATE MESSAGE-ID RECEIVED REPLY-TO)])'
        )

        # Occasionally we get non-message elements back
        messages.extend([item for item in data if len(item) == 2])


    for query, headers in messages:
        matches = re.match('^\d+', query)
        message_id = matches.group(0)

        header_hash = md5.new(headers.strip()).hexdigest()

        if header_hash not in seen_messages:
            seen_messages[header_hash] = message_id
        else:
            duplicate_messages[header_hash].add(message_id)


    for header_hash, message_list in duplicate_messages.items():
        print '\rDeleting %s duplicates of message %s...' % \
            (len(message_list), seen_messages[header_hash]),

        sys.stdout.flush()

        msg_ids = ','.join(message_list)
        typ, response = c.store(msg_ids, '+FLAGS', '\\Deleted')


    print '\nExpunging messages...',
    c.expunge()

finally:
    try:
        c.close()
    except:
        pass
    c.logout()

print '\rDuplicate deletion complete!'
