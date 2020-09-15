"""
There is only one operator!
Running on node prime.
"""
# internal imports
import os,sys; sys.path.append(os.path.abspath(os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__),'..')),'..')))
from komrade import *
from komrade.backend import *
from komrade.backend.messages import Message

# print(PATH_OPERATOR_WEB_KEYS_URL)

# def TheOperator(*x,**y):
#     from komrade.backend.operators import Komrade
#     return Komrade(OPERATOR_NAME,*x,**y)
OP_PRIVKEY = None

class TheOperator(Operator):
    """
    The remote operator
    """
    @property
    def phone(self):
        global TELEPHONE
        from komrade.backend.the_telephone import TheTelephone
        if not TELEPHONE: TELEPHONE=TheTelephone()
        return TELEPHONE
    

    def __init__(self, name = OPERATOR_NAME, passphrase=None):
        """
        Boot up the operator. Requires knowing or setting a password of memory.
        """
        global OP_PRIVKEY

        super().__init__(
            name,
            path_crypt_keys=PATH_CRYPT_OP_KEYS,
            path_crypt_data=PATH_CRYPT_OP_DATA
        )
        from komrade.backend.phonelines import check_phonelines
        keychain = check_phonelines()[OPERATOR_NAME]
        self._keychain = {**self.load_keychain_from_bytes(keychain)}

        if not keychain.get('pubkey'):
            raise KomradeException('Operator cannot find its own public key? Shutting down.')

        # check I match what's on op page
        pub_web = komrade_request(PATH_OPERATOR_WEB_KEYS_URL)
        if pub_web.status_code!=200:
            raise KomradeException("Can't verify Komrade Operator. Shutting down.")
        
        # print('Public key on komrade.app/pub:   ',pub_web.text)
        # print('Public key hardcoded in client:  ',keychain.get('pubkey').data_b64_s)
        
        if pub_web.text == keychain.get('pubkey').data_b64_s:
            # print('Pubs match')
            pass
        else:
            raise KomradeException('Public key for Operator on app and one at {PATH_OPERATOR_WEB_KEYS_URL} do not match. Shutting down.')

        privkey=None
        if os.path.exists(PATH_SUPER_SECRET_OP_KEY):
            
            if OP_PRIVKEY:
                privkey=OP_PRIVKEY
            else:
                print('Dare I claim to be the one true Operator?')
                with open(PATH_SUPER_SECRET_OP_KEY,'rb') as f:
                    #pass_encr=f.read()
                    privkey = f.read()
                    # try:
                    #     privkey=KomradeSymmetricKeyWithPassphrase().decrypt(pass_encr)
                    #     if privkey: OP_PRIVKEY = privkey
                    # except ThemisError:
                    #     exit('invalid password. operator shutting down.')
        if privkey:
            self._keychain['privkey']=KomradeAsymmetricPrivateKey(b64dec(privkey))
            # print(self._keychain['privkey'],'??')
        self._keychain = {**self.keychain()}
        # self.log('@Operator booted with keychain:',dict_format(self._keychain),'and passphrase',self.passphrase)
        # clear_screen()

        
        

    def ring(self,
        from_caller=None,
        to_caller=None,
        json_phone2phone={}, 
        json_caller2phone={},   # (person) -> operator or operator -> (person)
        json_caller2caller={}):
        
        encr_msg_to_send = super().ring(
            from_phone=self,
            to_phone=self.phone,
            from_caller=from_caller,
            to_caller=to_caller,
            json_phone2phone=json_phone2phone, 
            json_caller2phone=json_caller2phone,   # (person) -> operator
            json_caller2caller=json_caller2caller)

        return self.send(encr_msg_to_send)

    # ends the ring_ring() chain
    def answer_phone(self,data_b):
        # route incoming call from the switchboard
        from komrade.cli.artcode import ART_OLDPHONE4
        

        self.log(f'''Hello, this is the Operator.{ART_OLDPHONE4}I heard you say:\n\n {b64enc_s(data_b)}''')
        #woops
        # unseal
        # self.log('got:',data_b)
        msg_d = {
            'msg':data_b,
            'from_name':self.phone.name,
            'from':self.phone.pubkey.data,
            'to_name':self.name,
            'to':self.pubkey.data,
        }
        # msg_d = pickle.loads(data_b)
        # self.log('msg_d',msg_d)
        msg_obj = Message(msg_d)
        
        self.log(f'Decoding the binary, I discovered an encrypted message from {self.phone}\n: {msg_obj}')
        
        # decrypt?
        msg_obj.decrypt()

        # carry out message instructions
        resp_msg_obj = self.route_msg(msg_obj,reencrypt=True) #,route=msg_obj.route)
        self.log('Response from message routing:',resp_msg_obj)

        # send back down encrypted
        # self.log('route msgd',dict_format(resp_msg_obj.msg_d))
        # self.log('route msg',resp_msg_obj.msg)
        # self.log('route msg data',resp_msg_obj.data)
        # self.log('route msg obj',resp_msg_obj)


        
        msg_sealed = pickle.dumps(resp_msg_obj.msg_d)
        # self.log('msg_sealed =',msg_sealed)

        # return back to phone and back down to chain
        return msg_sealed

    def has_user(self,name=None,pubkey=None):
        nm,pk = name,pubkey
        if pubkey: pk=self.crypt_keys.get(
            name,
            prefix='/pubkey/'
        )
        if name: nm=self.crypt_keys.get(
            b64enc(pubkey),
            prefix='/name/'
        )
        self.log(f'checking whether I have user {name} and {pubkey},\n I discovered I had {nm} and {pk} on record')
        # self.log('pks:',pubkey,pk)
        # self.log('nms:',name,nm)
        return (pubkey and pk) or (name and nm)



    def send(self,encr_data_b):
        self.log(type(encr_data_b),encr_data_b,'sending!')
        return encr_data_b

    ### ROUTES
        


        
    def does_username_exist(self,msg_obj):
        data=msg_obj.data
        name=data.get('name')
        pubkey=self.crypt_keys.get(name,prefix='/pubkey/')
        self.log(f'looking for {name}, found {pubkey} as pubkey')
        return bool(pubkey)


    def login(self,msg_obj):
        data=msg_obj.data
        name=data.get('name')
        pubkey=data.get('pubkey')
        secret_login=data.get('secret_login')

        name=name.encode() if type(name)==str else name
        pubkey=pubkey.encode() if type(pubkey)==str else pubkey
        secret_login=secret_login.encode() if type(secret_login)==str else secret_login
        # get my records
        uri = b64enc(pubkey)
        name_record = self.crypt_keys.get(
            uri,
            prefix='/name/'
        )
        pubkey_record = b64enc(self.crypt_keys.get(
            name,
            prefix='/pubkey/'
        ))
        secret_record = b64enc(self.crypt_keys.get(
            uri,
            prefix='/secret_login/'
        ))


        self.log(f'''Checking inputs:
        
{name} (input)
 vs.
{name_record} (record)

{uri} (input)
 vs.
{pubkey_record} (record)

{secret_login} (input)
 vs.
{secret_record} (record)
''')
        
        # stop
        # check name?
        if name != name_record:
            self.log('names did not match!')
            success = False 
        # # check pubkey?
        elif uri != pubkey_record:
            self.log('pubkeys did not match!',uri,pubkey_record)
            success = False
        elif secret_login != secret_record:
            self.log('secrets did not match!')
            success = False
        else:
            success = True

        ## return res
        if success:
            return {
                'success': True,
                'status':f'Welcome back, Komrade @{name.decode()}.'
            }
        else:
            return {
                'success': False,
                'status':'Login failed.'
            }

    def register_new_user(self,msg_obj):
        # self.log('setting pubkey under name')
        data=msg_obj.data
        name=data.get('name')
        pubkey=data.get('pubkey')

        # is user already there?
        if self.has_user(name=name,pubkey=pubkey):
            return {
                'success':False,
                'status': f"{OPERATOR_INTRO}I'm sorry, but I can't register the name of {name}. This user already exists."
            }
        
        # generate shared secret
        shared_secret = get_random_binary_id()
        self.log(f'{self}: Generated shared secret between {name} and me:\n\n{make_key_discreet(shared_secret)}')

        # ok then set what we need
        uri_id = b64enc(pubkey)
        pubkey_b = b64dec(pubkey)
        r1=self.crypt_keys.set(name,pubkey_b,prefix='/pubkey/')
        r2=self.crypt_keys.set(uri_id,name,prefix='/name/')
        # hide secret as key
        r3=self.crypt_keys.set(uri_id,shared_secret,prefix='/secret_login/')

        # success?
        success = r1 and r2 and r3
        if not success:
            return {
                'success':False,
                'status': f"{OPERATOR_INTRO}I'm sorry, but I can't register the name of {name}."
            }

        # compose result
        res = {
            'success':success,
            'pubkey':pubkey_b,
            'secret_login':shared_secret,
            'name':name,
        }
        # res_safe = {
        #     **res, 
        #     **{
        #         'secret_login':make_key_discreet(
        #             res['secret_login']
        #         )
        #     }
        # }

        # return
        self.log('Operator returning result:',dict_format(res,tab=4))
        return res
        

        ## success msg
        #
        # cvb64=cv_b64#b64encode(cv).decode()
        # qrstr=self.qr_str(cvb64)
        # res['status']=self.status(f'''{OPERATOR_INTRO}I have successfully registered Komrade {name}.
        
        # If you're interested, here's what I did. I stored the public key you gave me, {cvb64}, under the name of "{name}". However, I never save that name directly, but record it only in a disguised, "hashed" form: {ck}. I scrambled "{name}" by running it through a 1-way hashing function, which will always yield the same result: provided you know which function I'm using, and what the secret "salt" is that I add to all the input, a string of text which I keep protected and encrypted on my local hard drive.
        
        # The content of your data will therefore not only be encrypted, but its location in my database is obscured even to me. There's no way for me to reverse-engineer the name of {name} from the record I stored it under, {ck}. Unless you explictly ask me for the public key of {name}, I will have no way of accessing that information.
        
        # Your name ({name}) and your public key ({cvb64}) are the first two pieces of information you've given me about yourself. Your public key is your 'address' in Komrade: in order for anyone to write to you, or for them to receive messages from you, they'll need to know your public key (and vise versa). The Komrade app should store your public key on your device as a QR code, under ~/.komrade/.contacts/{name}.png. It will look something like this:{qrstr}You can then send this image to anyone by a secure channel (Signal, IRL, etc), or tell them the code directly ({cvb64}).

        # By default, if anyone asks me what your public key is, I won't tell them--though I won't be able to avoid hinting that a user exists under this name should someone try to register under that name and I deny them). Instead, if the person who requested your public key insists, I will send you a message (encrypted end-to-end so only you can read it) that the user who met someone would like to introduce themselves to you; I will then send you their name and public key. It's now your move: up to you whether to save them back your public key.

        # If you'd like to change this default behavior, e.g. by instead allowing anyone to request your public key, except for those whom you explcitly block, I have also created a super secret administrative record for you to change various settings on your account. This is protected by a separate encryption key which I have generated for you; and this key which is itself encrypted with the password you entered earlier. Don't worry: I never saw that password you typed, since it was given to me already hashed and disguised. Without that hashed passphrase, no one will be able to unlock the administration key; and without the administration key, they won't be able to find the hashed record I stored your user settings under, since I also salted that hash with your own hashed passphrase. Even if someone found the record I stored them under, they wouldn't be able to decrypt the existing settings; and if they can't do that, I won't let them overwrite the record.''')
       
        # self.log('Operator returning result:',dict_format(res,tab=2))

    def deliver_msg(self,msg_to_op):
        data = msg_to_op.data
        deliver_to = data.get('deliver_to')
        deliver_from = data.get('deliver_from')
        deliver_msg = data.get('deliver_msg')

        if not deliver_to or not deliver_from or not deliver_msg:
            return {'success':False, 'status':'Invalid input.'}
        
        if b64enc(deliver_from) != b64enc(data['from']):
            return {'success':False, 'status':'Sender to me is not the sender of the message I am to forward'}

        to_komrade = Komrade(pubkey=deliver_to)
        from_komrade = Komrade(pubkey=deliver_from)
        deliver_to_b = b64dec(deliver_to)

        self.log(f'''Got:
data = {data}
deliver_to = {deliver_to}
deliver_from = {deliver_from}
deliver_msg = {deliver_msg}

to_komrade = {to_komrade}
from_komrade = {from_komrade}
''')    

        ## just deliver?
        
        from komrade.backend.messages import Message
        msg_from_op = Message(
            from_whom=self,
            msg_d = {
                'to':data.get('deliver_to'),
                'to_name':data.get('deliver_to_name'),
                
                'msg':{
                    
                    'to':data.get('deliver_to'),
                    'to_name':data.get('deliver_to_name'),
                    'from':data.get('deliver_from'),
                    'from_name':data.get('deliver_from_name'),
                    'msg':data.get('deliver_msg'),
                },

                'note':'Someone (marked "from") would like to send you (marked "to") this message (marked "msg").'
            }
        )

        self.log(f'{self}: Prepared this msg for delivery:\n{msg_from_op}')

        # encrypt
        msg_from_op.encrypt()

        return self.actually_deliver_msg(msg_from_op)

    def actually_deliver_msg(self,msg_from_op):
        msg_from_op_b_encr = msg_from_op.msg     #.msg_b  # pickle of msg_d
        self.log('got this:',msg_from_op_b_encr)
        deliver_to = msg_from_op.to_pubkey
        deliver_to_b = b64dec(deliver_to)

        # save new post
        post_id = get_random_binary_id()
        self.crypt_keys.set(
            post_id,
            msg_from_op_b_encr,
            prefix='/post/'
        )

        # get inbox
        inbox_old_encr = self.crypt_keys.get(deliver_to,prefix='/inbox/')
        
        if inbox_old_encr:
            inbox_old = SMessage(
                self.privkey.data,
                deliver_to_b
            ).unwrap(inbox_old_encr) #.split(BSEP)
        else:
            inbox_old=b''
        self.log('reloaded inbox:',inbox_old)

        # add new inbox
        inbox_new = post_id + (BSEP+inbox_old if inbox_old else b'')
        self.log('new inbox = ',inbox_new)

        # reencrypt
        inbox_new_encr = SMessage(
            self.privkey.data,
            deliver_to_b
        ).wrap(inbox_new)

        # encrypt
        self.log('new inbox encr:',inbox_new_encr)
        # save back to crypt
        self.crypt_keys.set(
            deliver_to,
            inbox_new_encr,
            prefix='/inbox/',
            override=True
        )

        return {
            'status':'Message delivered.',
            'success':True,
            'post_id':post_id
        }

    def check_msgs(self,
            msg_to_op,
            required_fields = [
                'secret_login',
                'name',
                'pubkey',
                'inbox',
            ]):

        # logged in?
        login_res = self.login(msg_to_op)
        if not login_res.get('success'):
            return login_res
        
        # ok, then find the inbox?
        inbox=msg_to_op.data.get('inbox')
        if not inbox: inbox=msg_to_op.data.get('pubkey')
        if not inbox: return {'success':False, 'status':'No inbox specified'}
        inbox_encr = self.crypt_keys.get(b64enc(inbox),prefix='/inbox/')

        # fine: here, try this on for size
        return {
            'status':'Succeeded in getting inbox.',
            'success':True,
            'data_encr':inbox_encr
        }
    
    def download_msgs(self,
            msg_to_op,
            required_fields = [
                'secret_login',
                'name',
                'pubkey',
                'post_ids',
            ],
            delete_afterward=False):

        # logged in?
        login_res = self.login(msg_to_op)
        if not login_res.get('success'):
            return login_res
        
        # ok, then find the posts?
        post_ids=msg_to_op.data.get('post_ids',[])
        if not post_ids: return {'success':False, 'status':'No post_ids specified'}
        
        posts = {}
        for post_id in post_ids:
            post = self.crypt_keys.get(b64enc(post_id),prefix='/post/')
            if post:
                posts[post_id] = post
        self.log(f'I {self} found {len(posts)} for {msg_to_op.from_name}')

        # delete?
        if delete_afterward:
            # @hack: this a bit dangerous?
            for post_id in posts:
                self.crypt_keys.delete(
                    post_id,
                    prefix='/post/'
                )
                self.log('deleting post id',post_id,'...')
        
        return {
            'status':'Succeeded in downloading new messages.' + (' I\'ve already deleted these messages from the server.' if delete_afterward else ''),
            'success':True,
            'data_encr':posts
        }

    def introduce_komrades(self,msg_to_op):
        # logged in?
        login_res = self.login(msg_to_op)
        if not login_res.get('success'):
            return login_res
        
        data=msg_to_op.data
        self.log('Op sees data:',dict_format(data))



        meet_pubkey = self.crypt_keys.get(
            data.get('meet_name'),
            '/pubkey/'
        )
        self.log('found in crypt:',meet_pubkey)

        msg = Message(
            {
                'to':meet_pubkey,
                'to_name':data.get('meet_name'),
                'from':self.uri,
                'from_name':self.name,

                'msg': {
                    'type':'introdution',

                    'status':f'''Komrade {data.get("name")} would like to make your acquaintance. Their public key is {data.get("pubkey")}.''',

                    'meet_name': data.get('name'),

                    'meet_pubkey': data.get('pubkey')
                }
            }
        )
        msg.encrypt()
        # self.log('formed msg:',msg.msg_d)

        return self.actually_deliver_msg(msg)


def test_op():
    from komrade.backend.the_telephone import TheTelephone

    from getpass import getpass
    op = TheOperator()
    # op.boot()
    
    keychain_op = op.keychain()

    
    phone = TheTelephone()
    # phone.boot()
    keychain_ph = phone.keychain()
    
    
    from pprint import pprint
    print('REASSEMBLED OPERATOR KEYCHAIN')
    pprint(keychain_op)
    # stop

    print('REASSEMBLED TELEPHONE KEYCHAIN')
    pprint(keychain_ph)
    
    # print(op.pubkey(keychain=keychain))
    # print(op.crypt_keys.get(op.pubkey(), prefix='/privkey_encr/'))
    # print(op.crypt_keys.get(op.name, prefix='/pubkey_encr/'))
    # print(op.pubkey_)


    # stop
    
    # pubkey = op.keychain()['pubkey']
    # pubkey_b64 = b64encode(pubkey)
    # print(pubkey)

if __name__ == '__main__': test_op()