#!/usr/bin/env python
import sqlite3
import json
import phonenumbers
import vobject
import logging


def get_contacts_from_android_db(database_file="contacts2.db"):
    db = sqlite3.connect(database_file)
    db.text_factory = lambda x: x.decode('utf-8')

    query = '''
    select m.mimetype
    , c._id as contact_id
    , c.display_name as display_name
    , d.data1
    , d.data2
    , d.data3
    , d.data4 
    , d.data5
    , d.data6
    , d.data7
    , d.data8
    , d.data9 
    , d.data10
    , d.data11
    , d.data12
    , d.data13
    , d.data14 
    , d.data15
    from data as d 
    
    inner join mimetypes as m, raw_contacts as c 
    on 
      m._id = d.mimetype_id and d.raw_contact_id = c._id 
    where 
       m.mimetype in ("vnd.android.cursor.item/name", "vnd.android.cursor.item/email_v2", "vnd.android.cursor.item/phone_v2", "vnd.android.cursor.item/postal-address_v2") 
    order by d.raw_contact_id
    ;
    '''


    raw_contacts = {}

    for mimetype, _id, display_name, data1, data2, data3, data4, data5, data6, data7, data8, data9, data10, data11, data12, data13, data14, data15 in db.execute(query):
        try:
            raw_contacts[_id].update({"display_name": display_name, "mimetypes":{}})
        except KeyError:
            raw_contacts[_id] = {"display_name": display_name, "mimetypes": {}}

        raw_contacts[_id]["mimetypes"][mimetype] = (data1, data2, data3, data4, data5, data6, data7, data8, data9, data10, data11, data12, data13, data14, data15)

    contacts = []
    vcards = []
    for _id, raw_contact in raw_contacts.items():
        contact = {
            "display_name": raw_contact['display_name']
        }

        vcard = vobject.vCard()
        vcard.add('fn')
        vcard.fn.value = raw_contact['display_name']

        for mimetype, data in raw_contact['mimetypes'].items():
            if mimetype == "vnd.android.cursor.item/name":
                contact["firstname"] = data[1] or ""
                contact["lastname"] = data[2] or ""
                vcard.add("n").value = vobject.vcard.Name(family=contact["lastname"], given=contact["firstname"])
            elif mimetype == "vnd.android.cursor.item/email_v2":
                contact["email"] = data[0] or ""
                vcard.add('email')
                vcard.email.value = data[0]
                vcard.email.type_param = 'INTERNET'
            elif mimetype == "vnd.android.cursor.item/phone_v2":
                try:
                    pnumber = phonenumbers.parse(data[0], "SE", keep_raw_input=True)
                    contact["phone_number"] = "+{country_code}{national_number}".format(
                        country_code=pnumber.country_code,
                        national_number=pnumber.national_number,
                    )
                    vcard.add("tel").value = contact['phone_number']

                except phonenumbers.NumberParseException as e:
                    logging.error("%s is not a phone number, %s", data[0], e)

            elif mimetype == "vnd.android.cursor.item/postal-address_v2":
                contact["address"] = data[0]
                contact["street"] = data[3] or ""
                contact["city"] = data[6] or ""
                contact["postcode"] = data[8] or ""
                contact["country"] = data[9] or ""
                vaddr = vobject.vcard.Address(street=data[3], city=contact["city"].title(), code=contact["postcode"], country=contact["country"].title())
                vcard.add('adr').value = vaddr
            else:
                logging.warning("Unknown mimetype")

            contacts.append(contact)
            vcards.append(vcard)
    return vcards, contacts


if __name__ == '__main__':
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("database", help="SQLite3 Android database from the contact provider")
    parser.add_argument("--vcards", help="Filename to gather the vCards")
    cmd_args = parser.parse_args()

    vcards, contacts = get_contacts_from_android_db(cmd_args.database)

    if cmd_args.vcards is not None:
        with open(cmd_args.vcards, "w") as buf:
            for vc in vcards:
                vc.serialize(buf)

    print(json.dumps(contacts, indent=2))
