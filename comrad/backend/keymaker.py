import os,sys; sys.path.append(os.path.abspath(os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__),'..')),'..')))
from comrad import *
from comrad.backend.crypt import *
from abc import ABC, abstractmethod

# common external imports
from pythemis.skeygen import KEY_PAIR_TYPE, GenerateKeyPair
from pythemis.smessage import SMessage, ssign, sverify
from pythemis.skeygen import GenerateSymmetricKey
from pythemis.scell import SCellSeal
from pythemis.exception import ThemisError

import logging 
logger=logging.getLogger(__name__)

 
class ComradKey(ABC,Logger):
    @abstractmethod
    def encrypt(self,msg,**kwargs): pass
    @abstractmethod
    def decrypt(self,msg,**kwargs): pass
    @abstractmethod
    def data(self): pass
    @property
    def data_b64(self):return b64encode(self.data) if type(self.data)==bytes else self.data.data_b64
    @property
    def data_b64_s(self):
        return self.data_b64.decode()
    @property
    def discreet(self): return make_key_discreet(self.data)
    def __str__(self):
        return repr(self)


class ComradSymmetricKey(ComradKey):
    def encrypt(self,msg,**kwargs):
        if hasattr(msg,'data'): msg=msg.data
        # print('??? dec',msg,kwargs)
        
        return self.cell.encrypt(msg,**kwargs)
    def decrypt(self,msg,**kwargs):
        if hasattr(msg,'data'): msg=msg.data
        # print('??? dec',msg,kwargs)
        
        try:
            return self.cell.decrypt(msg,**kwargs)
        except TypeError:
            return self.cell.decrypt(msg.data,**kwargs)


def getpass_status(passphrase=None):
    while not passphrase:
        passphrase1 = getpass(f'@Keymaker: What is a *memorable* pass word or phrase? Do not write it down.\n@{name}: ')
        passphrase2 = getpass(f'@Keymaker: Could you repeat that?')
        if passphrase1!=passphrase2:
            self.status('@Keymaker: Those passwords didn\'t match. Please try again.',clear=False,pause=False)
        else:
            return passphrase1

# get_pass_func = getpass_status if SHOW_STATUS else getpass
from getpass import getpass
        
class ComradSymmetricKeyWithPassphrase(ComradSymmetricKey):
    def hash(self,x): return self.crypt_keys.hash(x)

    @property
    def passhash(self):
        if not self._passhash:
            try:
                self._passhash = hasher(self.getpass_func(WHY_MSG))
            except (KeyboardInterrupt,EOFError) as e:
                exit('@Keymaker: Incorrect password. Goodbye.')
        return self._passhash

    def __init__(self,passphrase=None,passhash=None,getpass_func=None):
        self.getpass_func = getpass_func if getpass_func else getpass
        # logger.info('Pass key started with getpass func:',self.getpass_func)
        if passhash:
            self._passhash = passhash
        elif passphrase:
            self._passhash = hasher(passphrase)
        else:
            self._passhash = None
        

    @property
    def data(self): return KEY_TYPE_SYMMETRIC_WITH_PASSPHRASE.encode('utf-8')
    
    def __repr__(self): return f'[Symmetric Key] (generated by password)'
    
    @property
    def cell(self):
        if not hasattr(self,'_cell'):
            from getpass import getpass
            self._cell = SCellSeal(passphrase=self.passhash)
        return self._cell


class ComradSymmetricKeyWithoutPassphrase(ComradSymmetricKey):
    def __init__(self,key=None):
        self.key = GenerateSymmetricKey() if not key else key
    @property
    def data(self): return self.key
    def __repr__(self): return f'[Symmetric Key]\n({self.discreet})'
    @property
    def cell(self):
        if not hasattr(self,'_cell'):
            self._cell = SCellSeal(key=self.key)
        return self._cell



class ComradAsymmetricKey(ComradKey):
    def __init__(self,pubkey=None,privkey=None):
        if not pubkey or not privkey:
            keypair = GenerateKeyPair(KEY_PAIR_TYPE.EC)
            privkey = keypair.export_private_key()
            pubkey = keypair.export_public_key()
        self.pubkey=pubkey
        self.privkey=privkey    
        self.privkey_obj = ComradAsymmetricPrivateKey(privkey,pubkey)
        self.pubkey_obj = ComradAsymmetricPublicKey(pubkey,privkey)

    def encrypt(self,msg,pubkey=None,privkey=None):
        if issubclass(type(msg), ComradKey) or issubclass(type(msg), ComradEncryptedKey): msg=msg.data
        pubkey=pubkey if pubkey else self.pubkey
        privkey=privkey if privkey else self.privkey
        return SMessage(privkey,pubkey).wrap(msg)
    def decrypt(self,msg,pubkey=None,privkey=None):
        if issubclass(type(msg), ComradKey) or issubclass(type(msg), ComradEncryptedKey): msg=msg.data
        pubkey=pubkey if pubkey else self.pubkey
        privkey=privkey if privkey else self.privkey
        return SMessage(privkey.data,pubkey.data).unwrap(msg)
    @property
    def data(self): return self.key
    
class ComradAsymmetricPublicKey(ComradAsymmetricKey):
    def __init__(self,pubkey,privkey=None):
        self.pubkey=pubkey
        self.privkey=privkey
    @property
    def key(self): return self.pubkey
    @property
    def data(self): return self.pubkey 
    
    def __repr__(self): return f'''[Asymmetric Public Key]\n({self.data_b64.decode()})'''
class ComradAsymmetricPrivateKey(ComradAsymmetricKey):
    def __init__(self,privkey,pubkey=None):
        self.pubkey=pubkey
        self.privkey=privkey
    @property
    def data(self): return self.privkey 
    @property
    def key(self): return self.privkey
    def __repr__(self): return f'''[Asymmetric Private Key]\n({self.discreet})'''

def make_key_discreet(data,chance_unredacted=0.25):
    import random

    if not data: return '?'
    if not isBase64(data): data=b64encode(data)
    key=data.decode()

    return ''.join((k if random.random()<chance_unredacted else '-') for k in key)
    # return ''.join((k if not i%6 or not i%3 else '-') for i,k in enumerate(key))


def make_key_discreet_str(string,chance_unredacted=0.25):
    import random
    if not string: return '?'
    return ''.join((k if random.random()<chance_unredacted else '-') for k in string)


def make_key_discreet1(data,len_start=10,len_end=10,ellipsis='.',show_len=True):
    if not data: return '?'
    if not isBase64(data): data=b64encode(data)
    data=data.decode()
    amt_missing = len(data) - len_start - len_end
    dstr = data[:len_start] + (ellipsis*amt_missing)
    if len_end: dstr+=data[-len_end:]
    return f'{dstr}' #' (+{len(data)-len_start-len_end})'

class ComradEncryptedKey(Logger):
    def __init__(self,data): self.data=data
    @property
    def data_b64(self): return b64encode(self.data).decode()
    def __repr__(self): return f'[Encrypted Key]\n({self.discreet})'
    @property
    def discreet(self): return make_key_discreet(self.data)
    def __str__(self):
        return repr(self)

class ComradEncryptedAsymmetricPrivateKey(ComradEncryptedKey):
    def __repr__(self): return f'[Encrypted Asymmetric Private Key]\n({self.discreet})'
class ComradEncryptedAsymmetricPublicKey(ComradEncryptedKey):
    def __repr__(self): return f'[Encrypted Asymmetric Public Key]\n({self.discreet})'
class ComradEncryptedSymmetricKey(ComradEncryptedKey):
    def __repr__(self): return f'[Encrypted Symmetric Key]\n({self.discreet})'



KEYMAKER_DEFAULT_KEY_TYPES = {
    'pubkey':ComradAsymmetricPublicKey,
    'privkey':ComradAsymmetricPrivateKey,
    'adminkey':ComradSymmetricKeyWithoutPassphrase,
    
    'pubkey_decr':ComradSymmetricKeyWithoutPassphrase,
    'privkey_decr':ComradSymmetricKeyWithPassphrase,
    'adminkey_decr':ComradSymmetricKeyWithPassphrase,

    'pubkey_decr_decr':ComradSymmetricKeyWithoutPassphrase,
    'privkey_decr_decr':ComradSymmetricKeyWithPassphrase,
    'adminkey_decr_decr':ComradSymmetricKeyWithPassphrase,

    'pubkey_encr_decr':ComradSymmetricKeyWithoutPassphrase,
    'privkey_encr_decr':ComradSymmetricKeyWithPassphrase,
    'adminkey_encr_decr':ComradSymmetricKeyWithPassphrase,


    # encrypted keys
    'pubkey_encr':ComradEncryptedAsymmetricPublicKey,
    'privkey_encr':ComradEncryptedAsymmetricPrivateKey,
    'adminkey_encr':ComradEncryptedSymmetricKey,
    'pubkey_encr_encr':ComradEncryptedSymmetricKey,
    'privkey_encr_encr':ComradEncryptedSymmetricKey,
    'adminkey_encr_encr':ComradEncryptedSymmetricKey,
    'pubkey_decr_encr':ComradEncryptedSymmetricKey,
    'privkey_decr_encr':ComradEncryptedSymmetricKey,
    'adminkey_decr_encr':ComradEncryptedSymmetricKey
}





def get_key_obj(keyname,data,key_types=KEYMAKER_DEFAULT_KEY_TYPES,getpass_func=None,passphrase=None):
    if keyname.endswith('_decr'):
        # print('get_key_obj',keyname,data)#,key_types)
        try:
            data_s = data.decode()
            if data_s in {KEY_TYPE_SYMMETRIC_WITH_PASSPHRASE,ComradSymmetricKeyWithPassphrase.__name__}:
                return ComradSymmetricKeyWithPassphrase(getpass_func=getpass_func,passphrase=passphrase)
        except UnicodeDecodeError:
            return ComradSymmetricKeyWithoutPassphrase(data)

    return key_types[keyname](data)









class Keymaker(Logger):
    def __init__(self,
                name=None,
                uri_id=None,
                keychain={},
                path_crypt_keys=PATH_CRYPT_CA_KEYS,
                path_crypt_data=PATH_CRYPT_CA_DATA,
                callbacks={},
                getpass_func=None):
        
        # init logger with callbacks
        super().__init__(callbacks=callbacks)

        # set defaults
        self.name=name
        self._uri_id=uri_id
        self._pubkey=None
        self._keychain={**keychain}
        self.path_crypt_keys=path_crypt_keys
        self.path_crypt_data=path_crypt_data
        self.getpass_func=getpass_func
        # logger.info('Keymaker booted with getpass_func',getpass_func)

        # boot keychain
        # self._keychain = self.keychain()


    def find_pubkey(self,name=None):
        self.log('<-',name)
        if not name: name=self.name
        self.log('<---',name)
        if self.name==name and 'pubkey' in self._keychain and self._keychain['pubkey']:
            pk=self._keychain['pubkey']
            return ComradAsymmetricPublicKey(b64dec(pk)) if type(pk)==bytes else pk
        
        res = self.crypt_keys.get(name, prefix='/pubkey/')
        self.log(f'crypt_keys({name}) -->',res)
        if not res:
            res = self.load_qr(name)
            self.log(f'load_qr({name}) -->',res)
        if not res: return
        key = ComradAsymmetricPublicKey(b64dec(res))
        self.log('-->',key)
        return key
        # self.log('I don\'t know my public key! Do I need to register?')
        # raise ComradException(f'I don\'t know my public key!\n{self}\n{self._keychain}')
        # return res

    def find_name(self,pubkey_b64):
        res = self.crypt_keys.get(b64enc(pubkey_b64), prefix='/name/')
        if res: res=res.decode()
        return res

    @property
    def keys(self):
        return sorted(list(self.keychain().keys()))
    
    @property
    def top_keys(self):
        return [k for k in self.keys if k.count('_')==0]

    def load_keychain_from_bytes(self,keychain):
        for keyname,keyval in keychain.items():
            keychain[keyname] = get_key_obj(keyname,keyval,getpass_func=self.getpass_func)
        return keychain

    def keychain(self,look_for=KEYMAKER_DEFAULT_ALL_KEY_NAMES,passphrase=None):
        # load existing keychain
        keys = self._keychain
        
        # get uri
        pubkey = self.find_pubkey()
        if pubkey:
            keys['pubkey'] = pubkey

            uri = pubkey.data_b64
            #uri = b64encode(pubkey) if type(pubkey)==bytes else b64encode(pubkey.encode())
            # get from cache
            for keyname in look_for:
                # print(self.name,'looking for key:',keyname)
                if keyname in keys and keys[keyname]: continue
                key = self.crypt_keys.get(uri,prefix=f'/{keyname}/')
                # print('found in crypt:',key,'for',keyname)
                if key: keys[keyname]=get_key_obj(keyname,key,getpass_func=self.getpass_func,passphrase=passphrase)
        
        # try to assemble
        keys = self.assemble(self.assemble(keys,passphrase=passphrase),passphrase=passphrase)
        
        #store to existing set
        self._keychain = {**keys}
        
        #return
        return keys


    @property
    def pubkey(self): return self.keychain().get('pubkey')
    @property
    def pubkey_b64(self): return b64encode(self.pubkey) #self.keychain().get('pubkey')
    @property
    def privkey(self): return self.keychain().get('privkey')
    @property
    def adminkey(self): return self.keychain().get('adminkey')
    @property
    def pubkey_encr(self): return self.keychain().get('pubkey_encr')
    @property
    def privkey_encr(self): return self.keychain().get('privkey_encr')
    @property
    def adminkey_encr(self): return self.keychain().get('adminkey_encr')
    @property
    def pubkey_decr(self): return self.keychain().get('pubkey_decr')
    @property
    def privkey_decr(self): return self.keychain().get('privkey_decr')
    @property
    def adminkey_decr(self): return self.keychain().get('adminkey_decr')


    def load_qr(self,name):
        if not name: return
        # try to load?
        contact_fnfn = os.path.join(PATH_QRCODES,name+'.png')
        if not os.path.exists(contact_fnfn): return ''
        # with open(contact_fnfn,'rb') as f: dat=f.read()
        from pyzbar.pyzbar import decode
        from PIL import Image
        res= decode(Image.open(contact_fnfn))[0].data

        # self.log('QR??',res,b64decode(res))
        return b64decode(res)

    @property
    def uri_id(self):
        if not self._uri_id:
            pubkey = self.pubkey #find_pubkey()
            self._uri_id = pubkey.data_b64
        return self._uri_id

    @property
    def uri(self):
        return self.uri_id

    ### BASE STORAGE
    @property
    def crypt_keys(self):
        if not hasattr(self,'_crypt_keys'):
            self._crypt_keys = Crypt(
                fn=self.path_crypt_keys,
                encrypt_values=False
            )
        return self._crypt_keys

    @property
    def crypt_data(self):
        if not hasattr(self,'_crypt_data'):
            self._crypt_data = Crypt(
                fn=self.path_crypt_data,
                encrypt_values=False,
                # encryptor_func=self.encrypt,
                # decryptor_func=self.decrypt,
            )
        return self._crypt_data

    def encrypt(self,x):
        return self.privkey_decr.encrypt(x)
        # if 'privkey_decr' in self._keychain:
        #     self.log('! encrypting')
            
        # self.log('! not encrypting')
        # return x
    def decrypt(self,x):
        # if 'privkey_decr' in self._keychain:
            # self.log('! decrypting')
        return self.privkey_decr.decrypt(x)
        # self.log('! not decrypting')
        # return x



  
    def get_path_qrcode(self,name=None,dir=None,ext='.png'):
        if not name: name=self.name
        if not dir: dir = PATH_QRCODES
        fnfn = os.path.join(dir,name+ext)
        return fnfn

    @property
    def qr(self): return self.qr_str(data=self.uri_id)

    def qr_str(self,data=None):
        data = self.uri_id if not data else data
        return get_qr_str(data)
        

    def save_uri_as_qrcode(self,uri_id=None,name=None):
        if not uri_id: uri_id = self.uri_id
        if not uri_id and not self.uri_id: raise ComradException('Need URI id to save!')
        if not name: name=self.name

        # gen
        import pyqrcode
        qr = pyqrcode.create(uri_id)
        ofnfn = self.get_path_qrcode(name=name)
        qr.png(ofnfn,scale=5)
        
        self._uri_id = uri_id
        self.log(f'''Saved public key as QR code to:\n{ofnfn}\n\n{self.qr}''')
        return ofnfn

    def save_keychain(self,name,keychain,keys_to_save=None,uri_id=None):
        if not keys_to_save: keys_to_save = list(keychain.keys())
        if not uri_id and 'pubkey' in keychain:
            uri_id = b64encode(keychain['pubkey'].data).decode() #uri_id = get_random_id() + get_random_id()
        # self.log(f'SAVING KEYCHAIN FOR {name} under URI {uri_id}')
        self._uri_id = uri_id
        # filter for transfer
        for k,v in keychain.items():
            if issubclass(type(v),ComradKey):
                v=v.data
            keychain[k]=v
        
        # save keychain
        keys_saved_d={}
        for keyname in keys_to_save:
            if not '_' in keyname and keyname!='pubkey':
                self.log('there is no private property in a socialist network! all keys must be split between comrades',keyname)
            if keyname in keychain:
                # uri = uri_id
                uri = uri_id if keyname!='pubkey' else name
                if not uri: raise ComradException('invalid URI! {uri}')
                val = keychain[keyname]
                if issubclass(type(keychain[keyname]), ComradKey) or issubclass(type(keychain[keyname]), ComradEncryptedKey):
                    val = val.data
                self.crypt_keys.set(uri,val,prefix=f'/{keyname}/')
                keys_saved_d[keyname] = keychain[keyname]

        # save pubkey as QR
        if not 'pubkey' in keys_saved_d:
            # self.log('did not save pubkey in crypt, storing as QR...')
            self.save_uri_as_qrcode(name=name, uri_id=uri_id)

        # set to my keychain right away
        self._keychain = {**keychain}

        return (uri_id,keys_saved_d,keychain)

    def assemble(self,keychain,key_types=KEYMAKER_DEFAULT_KEY_TYPES,decrypt=True,passphrase=None):
        encr_keys = [k for k in keychain.keys() if k.endswith('_encr')]
        for encr_key_name in encr_keys:
            decr_key_name = encr_key_name[:-5] + '_decr'
            unencr_key_name = encr_key_name[:-5]
            # self.log(encr_key_name,decr_key_name,unencr_key_name)
            if decrypt and unencr_key_name in keychain: continue
            if not decr_key_name in keychain:
                self.log('! not in keychain: decr key name:',decr_key_name,keychain)
                continue
            decr_key = keychain.get(decr_key_name)
            try:
                if decrypt:
                    encr_key = keychain.get(encr_key_name)
                    # self.log(f'about to decrypt {encr_key} with {decr_key} and {decr_key.cell}')
                    unencr_key = decr_key.decrypt(encr_key.data)
                    keychain[unencr_key_name] = get_key_obj(unencr_key_name,unencr_key,getpass_func=self.getpass_func,passphrase=passphrase)
                else:
                    # unencr_key = keychain.get(unencr_key_name)
                    # self.log(f'about to encrypt {unencr_key} with {decr_key}')
                    encr_key = decr_key.encrypt(unencr_key.data)
                    keychain[encr_key_name] = get_key_obj(encr_key_name,encr_key,getpass_func=self.getpass_func,passphrase=passphrase)
            except ThemisError as e:
                #exit('Incorrect password.')
                #self.log('error!!',e,decrypt,decr_key,encr_key,decr_key_name,encr_key_name)
                pass

        return keychain

    def disassemble(self,keychain,**kwargs):
        return self.assemble(keychain,decrypt=False,**kwargs)


