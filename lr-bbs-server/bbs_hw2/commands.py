import dataparser as dp
import sqlite3
import os.path
import re
from datetime import date

'''
    {
        "boardName1":{
            "post1_SN":[SN,board,title,author,date,content]
            "post2_SN":[SN,board,title,author,date,content]
        }            
        "boardName2":{
            "post1_SN":[SN,board,title,author,date,content]
        }
        ......
    }
'''
class Post():
    counter = 0
    def __init__(self,board,title,author,date,content,available=True):
        if (available==True): 
            Post.counter += 1
        self.SN=Post.counter
        self.board=board
        self.title=title
        self.author=author
        self.date=date
        self.content=content
        self.comments=""
        self.available=available
    
    def read(self):
        c = self.content.split('<br>')
        msg = f"Author: {self.author}\nTitlte: {self.title}\nDate: {self.date}\n--\n"
        for comp in c:
            msg = msg + comp + '\n'
        msg = msg + '--' + self.comments
        return msg
    
    def update(self,ntype,new):
        if(ntype=="title"): self.title=new
        if(ntype=="content"): self.content=new
    
    def comment(self,user,comm):
        self.comments += f'\n{user}: {comm}'

def emptypost():
    return Post(0,0,0,0,0,False)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, 'userinf.db')

posts=[emptypost()]

def make_jsend(command,data):
    return { "command":command, "data":data }

def usrReg(username, email, password):
    con = sqlite3.connect(db_path)    
    c = con.cursor()
    c.execute(f"SELECT * FROM user WHERE name='{username}'")
    if c.fetchone() is None:
        c.execute(f"INSERT INTO USER VALUES (null,'{username}','{email}','{password}')")
        con.commit()
        con.close()
        return 0
    else:
        con.close()
        return -1

def usrlogin(username, password):
    con = sqlite3.connect(db_path)
    c = con.cursor()
    c.execute(f"SELECT * FROM user WHERE name='{username}' AND password='{password}'")
    result = c.fetchone()
    con.close()
    if result != None:
        return result[0]
    else: 
        return -1
    
def listusers():
    con = sqlite3.connect(db_path)
    c = con.cursor()
    msg = 'Name'.ljust(15, ' ') + 'Email'.ljust(20, ' ') + '\n'
    for row in c.execute('SELECT * FROM user ORDER BY id'):
        msg = msg + str(row[1]).ljust(15, ' ') + str(row[2]).ljust(20, ' ') + '\n'
    con.close()
    return msg

def listboards():
    con = sqlite3.connect(db_path)
    c = con.cursor()
    msg = 'Index'.ljust(15, ' ') + 'Name'.ljust(15, ' ') + 'Moderator'.ljust(15, ' ') + '\n'
    for row in c.execute('SELECT * FROM board ORDER BY "index"'):
        msg = msg + str(row[0]).ljust(15, ' ') + str(row[1]).ljust(15, ' ') + str(row[2]).ljust(15, ' ') + '\n'
    con.close()
    return msg
    

def addBoard(board_name,moderator):
    con = sqlite3.connect(db_path)    
    c = con.cursor()
    c.execute(f"SELECT * FROM BOARD WHERE name='{board_name}'")
    if c.fetchone() is None:
        c.execute(f"INSERT INTO BOARD VALUES (null,'{board_name}','{moderator}')")
        con.commit()
        con.close()
        return 0
    else:
        con.close()
        return -1
    
def postExist(post_SN):
    if (int(post_SN) <= Post.counter and posts[int(post_SN)].available == True): 
        return True
    else: 
        return False
    
def listposts(board_name):
    con = sqlite3.connect(db_path)    
    c = con.cursor()
    c.execute(f"SELECT * FROM BOARD WHERE name='{board_name}'")
    if c.fetchone() is None: return "Board does not exist."
    else:
        msg = 'S/N'.ljust(10, ' ') + 'Title'.ljust(15, ' ') + 'Author'.ljust(15, ' ') + 'Date'.ljust(15, ' ') + '\n'
        for p in posts:
            if (p.available == True and p.board == board_name) : 
                msg += str(p.SN).ljust(10, ' ') + p.title.ljust(15, ' ') + p.author.ljust(15, ' ') + p.date.ljust(15, ' ') + '\n'
        return msg
        
def addPost(board,title,author,content):
    con = sqlite3.connect(db_path)    
    c = con.cursor()
    c.execute(f"SELECT * FROM BOARD WHERE name='{board}'")
    if c.fetchone() is None:
        return -1
    else:
        global posts
        today = date.today()
        MD = f"{today.month}/{today.day}"
        #posts[board] = {f'{post_counter}:[{post_counter},{board},{title},{author},{MD},{content}]'}
        post = Post(board,title,author,MD,content)
        posts.append(post)
        return 0 

class tcpCmdHandler(dp.Data_Parser):
    command = dp.CommandListener("tcp")
    cmdlist = command.tcp_savecmds
    
    def __init__(self,lock):
        dp.Data_Parser.__init__(self,lock) 
        
        
    @command.listen()    
    def login(self,jMsg,username,password):
        if (jMsg["user"] != "none"):
            command = 'none'
            sendmsg = 'Please logout first!'
        else:
            uid = usrlogin(username,password)
            if (uid != -1):
                command = f'setuser {username} {uid}'
                sendmsg = f'Welcome, {username}.'
            else:
                command = 'none'
                sendmsg = 'Login failed.'        
        return make_jsend(command,sendmsg)
    
    @command.listen()    
    def logout(self,jMsg):
        if (jMsg["user"] != "none"):
            command = "logout"
            sendmsg = f"Bye, {jMsg['user']}"
        else:
            command = "none"
            sendmsg = "Please login first!"    
        return make_jsend(command,sendmsg)
    
    @command.listen(name="list-user")    
    def listuser(self,jMsg):
        command = "none"
        sendmsg = listusers()
        return make_jsend(command,sendmsg)
    
    @command.listen()    
    def exit(self,jMsg):
        command = "exit"
        sendmsg = ""
        return make_jsend(command,sendmsg)
    ######## Bulletin Board System ########
    
    @command.listen(name="create-board")
    def create_board(self,jMsg,name):
        if (jMsg["user"] == "none"):
            command = "none"
            sendmsg = "Please login first!"
        else:
            check = addBoard(name,jMsg["user"])
            if check == 0 :
                command = "none"
                sendmsg = "Create board successfully."
            else:
                command = "none"
                sendmsg = 'Board already exists.'
        return make_jsend(command,sendmsg)
    
    @command.listen(name="create-post", usage="<board-name> --title <title> --content <content>")
    def create_post(self,jMsg,board,title,content):
        if (jMsg["user"] == "none"):
            command = "none"
            sendmsg = "Please login first!"
        else:
            self.lock.acquire()
            check = addPost(board,title,jMsg['user'],content)
            self.lock.release()
            if check == 0 :
                command = "none"
                sendmsg = "Create post successfully."
            else:
                command = "none"
                sendmsg = "Board does not exist."
        return make_jsend(command,sendmsg)
    
    @command.listen(name="list-board")
    def list_board(self,jMsg):
        command = "none"
        sendmsg = listboards()
        return make_jsend(command,sendmsg)
    
    @command.listen(name="list-post", usage="<board-name>")
    def list_post(self,jMsg,board_name):
        self.lock.acquire()
        command = "none"
        sendmsg = listposts(board_name)
        self.lock.release()
        return make_jsend(command,sendmsg)
    
    @command.listen(usage="<post-S/N>")
    def read(self,jMsg,post_SN):
        self.lock.acquire()
        if( postExist(post_SN) ):
            command = "none"   
            sendmsg = posts[int(post_SN)].read()
        else:
            command = "none"
            sendmsg = "Post does not exist."
        self.lock.release()
        return make_jsend(command,sendmsg)

    @command.listen(name="delete-post", usage="<post-S/N>")
    def delete_post(self,jMsg,post_SN):
        
        if (jMsg["user"] == "none"):
            command = "none"
            sendmsg = "Please login first!"
        else:
            global posts
            self.lock.acquire()
            if (postExist(post_SN)):
                if(posts[int(post_SN)].author == jMsg['user']): 
                    posts[int(post_SN)] = emptypost()
                    command = "none"
                    sendmsg = "Delete successfully."
                else:
                    command = "none"
                    sendmsg = "Not the post owner."
            else:
                command = "none"
                sendmsg = "Post does not exist."   
            self.lock.release()
        return make_jsend(command,sendmsg)
    
    @command.listen(name="update-post", usage="<post-S/N> --title/content <new>")
    def update_post(self,jMsg,post_SN,which,inf):
        if (jMsg["user"] == "none"):
            command = "none"
            sendmsg = "Please login first!"
        else:
            global posts
            self.lock.acquire()
            if (postExist(post_SN)):
                if(posts[int(post_SN)].author == jMsg['user']): 
                    if(which=="title"):
                        posts[int(post_SN)].title = inf
                    if(which=="content"):
                        posts[int(post_SN)].content = infz 
                    command = "none"
                    sendmsg = "Update successfully."
                else:
                    command = "none"
                    sendmsg = "Not the post owner."
            else:
                command = "none"
                sendmsg = "Post does not exist."
            self.lock.release()
        return make_jsend(command,sendmsg)
    
    @command.listen(usage="<post-S/N> <comment>") 
    def comment(self,jMsg,post_SN,comment):
        if (jMsg["user"] == "none"):
            command = "none"
            sendmsg = "Please login first!"
        else:
            global posts
            self.lock.acquire()
            if (postExist(post_SN)):   
                posts[int(post_SN)].comment(jMsg['user'],comment)
                command = "none"
                sendmsg = "Comment successfully."
            else:
                command = "none"
                sendmsg = "Post does not exist."
            self.lock.release()
        return make_jsend(command,sendmsg)
    #####################################################

class udpCmdHandler(dp.Data_Parser):
    command = dp.CommandListener("udp")
    cmdlist = command.udp_savecmds
    
    def __init__(self,lock):
        dp.Data_Parser.__init__(self,lock)
    
    @command.listen()
    def hello(self,jMsg):
        command = "none"
        sendmsg = "hello!"
        return make_jsend(command,sendmsg)
    
    @command.listen()
    def register(self,jMsg,username,email,password):
        check = usrReg(username,email,password)
        if check == 0 :
            command = "none"
            sendmsg = "Register successfully."
        else: 
            command = "none"
            sendmsg = 'Username is already used.'
        return make_jsend(command,sendmsg)
        
    @command.listen()    
    def whoami(self,jMsg):
        if (jMsg["user"] != "none"):
            command = "none"
            sendmsg = jMsg["user"]
        else: 
            command = "none"
            sendmsg = "Please login first!"
        return make_jsend(command,sendmsg)
    
    @command.listen()
    def hi(self,jMsg):
        command = "none"
        sendmsg = "hi."
        return make_jsend(command,sendmsg)
