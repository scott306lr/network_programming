import re

class CommandListener:
    tcp_savecmds={}
    udp_savecmds={}
    
    def __init__(self,stype):
        self.stype = stype
        
    def add_listener(self, func, name=None, usage=None):
        #get inspect
        func_name = func.__name__ if (name==None) else name
        var_num   = func.__code__.co_argcount
        var_names = func.__code__.co_varnames[:var_num]
        
        #generate usage if passed parameter is incorrect
        #print(f"{func_name},{var_names},{var_num}")
        if (usage==None):
            func_usage = f"Usage: {func_name}"
            for name in var_names[2:] : func_usage += f" <{name}>"
            
        else:   
            func_usage = f"Usage: {func_name} " + usage
        
        #save cmd to dictionary
        cmd = {"exc":[func], "argcnt":var_num, "usage":func_usage}
        if  (self.stype=="tcp"): self.tcp_savecmds[func_name] = cmd
        elif(self.stype=="udp"): self.udp_savecmds[func_name] = cmd
        
    def listen(self, name=None, usage=None):
        def decorator(func):
            self.add_listener(func, name, usage)
            return func
        return decorator


class Data_Parser:
    #command = CommandListener()
    #cmdlist = command.savecmds
    cmdlist={}
    def __init__(self,lock):
        self.lock=lock
        
    def runcmd(self,jMsg):
        jres = {"command":"none", "data":"none"}
        try:
            cmd = jMsg["data"].split(' ',8)
            try :
                if ( cmd[0] == 'create-post') : 
                    cmd = jMsg["data"].split(' ',3)
                    cmd[2] = re.search(r'(?<=--title )(.*?)(?= --)',jMsg["data"]).group()
                    cmd[3] = re.search(r'(?<=--content )(.*)',jMsg["data"]).group()
                elif ( cmd[0] == 'update-post'):
                    cmd = jMsg["data"].split(' ',3)
                    reg = re.search(r'[^--]*$',jMsg["data"]).group().split(' ',1)
                    cmd[2] = reg[0]
                    cmd[3] = reg[1]
                elif ( cmd[0] == 'comment'):
                    cmd = jMsg["data"].split(' ',2)
                    
            except :
                cmd = jMsg["data"].split(' ',8)
            #print (f"Got data: {cmd}, len:{len(cmd[1:])}")
            
            func_inf = self.cmdlist[cmd[0]]
            if len(cmd[1:]) != func_inf['argcnt']-2 :
                jres["command"]="none"
                jres["data"] = func_inf['usage']
            else:
                #print(cmd[1:])
                jres = func_inf['exc'][0](self,jMsg,*cmd[1:])
            return jres
            
        except KeyError as e:
            print(f"Exception because of: {e}")
            jres["command"]="none"
            jres["data"]="Unknown!"
            return jres
        





