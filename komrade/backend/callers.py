import os,sys; sys.path.append(os.path.abspath(os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__),'..')),'..')))
from komrade import *
from komrade.backend import *
# from komrade.backend.the_telephone import *

# from komrade.backend.the_telephone import *


class Caller(Operator):
    """
    Variant of an Operator which handles local keys and keymaking.
    """


    def get_new_keys(self, name = None, passphrase = None, is_group=None):
        if not name: name=self.name
        if name is None: 
            name = input('\nWhat is the name for this account? ')
        if passphrase is None:
            passphrase = getpass.getpass('\nEnter a memborable password: ')
        # if is_group is None:
            # is_group = input('\nIs this a group account? [y/N]').strip().lower() == 'y'

        req_json = {
            '_route':'forge_new_keys',
            'name':name,
            'passphrase':hashish(passphrase.encode())
        }

        phone_res = self.phone.ring_operator(json_phone2phone=req_json)
        name = phone_res.get('name')
        returned_keys = phone_res.get('_keychain')
        self.log('got returnd keys from Op:',returned_keys)

        # better have the right keys
        assert set(req_json['keys_to_return']) == set(returned_keys.keys())

        # now save these keys!
        saved_keys = self.save_keychain(name,returned_keys)
        self.log('saved keys!',saved_keys)

        # better have the right keys
        assert set(req_json['keys_to_return']) == set(saved_keys.keys())

        # success!
        self.log('yay!!!!')
        return saved_keys
