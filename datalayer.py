# -*- coding: UTF-8 -*-
import mysql.connector
import json
import config
import sendgrid
from sendgrid.helpers.mail import *

CONFIG=config.Config().configDict
MAIL_ADMIN = "matimoya_06@hotmail.com"


class DataLayer():
    '''
        This class allow us to instantiate an object of datalayer class
    '''
    def __init__(self, configDict):
        '''
            Contructor method, allow us to receive a dictionary from config.py file with credentials values.
            :var configDict: Contain the credentials values

        '''
        userDB=configDict['user']
        PassDB=configDict['password']
        HostDB=configDict['host']
        database = configDict['dbname']
        Port = configDict['port']
        self.__conn = mysql.connector.connect(
            user=userDB,
            password=PassDB,
            host=HostDB,
            database=database,
            port=Port)

    def update_ifexist_verification(self,id_usr,ip,dashboard_url,status,session_id):
        '''
        this method update if exist one register for usr_auto_verification table
        '''
        try:
            cursor = self.__conn.cursor()
            sql="""INSERT INTO usr_auto_verification(id_usr,dashboard_url,verification_status,verification_ip,session_id) VALUES(%s,%s,%s,%s,%s) 
            ON DUPLICATE KEY UPDATE `dashboard_url` = VALUES(`dashboard_url`), 
            `verification_status` = VALUES(`verification_status`), 
            `verification_ip` = VALUES(`verification_ip`) , 
            `session_id` = VALUES(`session_id`)"""
            data=(id_usr,
                dashboard_url,
                status,
                ip,
                session_id)
            cursor.execute(sql,data)
            self.__conn.commit()
            cursor.close()
            self.__conn.close()
        except Exception as e:
            print('update_ifexist_verification Exception: '.format(e))
            try:
                if cursor:
                    cursor.close()
                    self.__conn.close()
            except Exception as e:
                # the connection already close
                pass
            raise
    
    def update_level_2(self,id_user,required_level,level_completed):
        '''
        this method update one register for usr_type_country_user table
        '''
        try:
            cursor = self.__conn.cursor()
            sql='UPDATE usr_type_country_user SET level_completed = %s, required_level = %s WHERE id_user = %s'
            data=(level_completed, required_level, id_user)
            cursor.execute(sql,data)
            self.__conn.commit()
            cursor.close()
            self.__conn.close()
        except Exception as e:
            print('update_level_2 Exception: '.format(e))
            try:
                if cursor:
                    cursor.close()
                    self.__conn.close()
            except Exception as e:
                # the connection already close
                pass
            raise
    
    def save_step(self, id_usr, event_name, event_date, error, session_id, hook):
        '''
        this method saves the steps completed by the user in usr_auto_verification_events table
        '''
        try:
            cursor = self.__conn.cursor()
            sql='INSERT INTO usr_auto_verification_events(id_usr,event_name,event_date,error,session_id,hook) VALUES(%s,%s,%s,%s,%s,%s)'
            data=(id_usr, event_name, event_date, error, session_id, json.dumps(hook))
            cursor.execute(sql,data)
            self.__conn.commit()
            cursor.close()
            self.__conn.close()
        except Exception as e:
            print(f"save_step Exception: {e}")
            try:
                if cursor:
                    cursor.close()
                    self.__conn.close()
            except Exception as e:
                # the connection already close
                pass
            raise

    def execute_query_dict(self, query):
        conn = mysql.connector.connect(
            user=CONFIG['user'],
            password=CONFIG['password'],
            host=CONFIG['host'],
            database=CONFIG['dbname'],
            port=CONFIG['port'])
        cur = conn.cursor()
        response = []
        res = {'code':500,'data':response}
        try:
            headers = []
            # Get all data from store procedure:
            cur.execute(query)
            results = cur.fetchall()
            headers = [i[0] for i in cur.description]
            cur.nextset()
            conn.commit()
            for x in results:
                data_json = dict()
                for key,value in enumerate(headers):
                    data_json[value]=x[key]
                response.append(data_json)
            res['data'] = response
            res['code'] = 200
        except Exception as e:
            print(f"Error execute_query_dict {e}")
            res['code'] = 500
            res['data'] = '[ERROR]'+str(e)
        finally:
            cur.close()
            conn.close()
            return res

    def webhook_mail(self, user_id, status, mati_url, session_id):
        """
            @param: {"user_id": 52122, "id_admin" : 0, "id_type_admin":1,"status" : "RJ", "id_reason_rejection" : 1, "platform":"blockzy"}
            @Descripcion: Recibe el id del documento y los datos para actualizar el mismo
        """
        try:
            res = "Algo salio mal y no se envío el correo"
            data = {"user_id": user_id, "id_admin": 0, "status": status, "id_type_admin": 1}
            if not data['status'] in ('AP', 'RJ', 'RN'):
                res = self.create_error_data({'msg': 'Status Invalido.'}, 400)
                return

            cursor = self.__conn.cursor()
            sql= f"SELECT usr.* FROM usr_user usr WHERE id_user = {data['user_id']}"
            cursor.execute(sql)
            select_query = cursor.fetchone()
            self.__conn.commit()
            cursor.close()
            self.__conn.close()

            if not select_query:
                res = self.create_error_data({'msg': 'No existe ningun usuario con ese ID.', 'cod:resp': '683'}, 500)
                return

            # Enviamos mail si esta AP o RJ
            if data['status'] == 'AP':

                template = self.structure_mail_verificationComplete(select_query[1])
                if not template['success']:
                    res = self.create_error_data({'msg': 'Error on template: ' + template['msg'], 'cod_resp': '615'}, 304)
                    return
                send = self.send_mail(select_query[2], template['datos'])
                if not send['success']:
                    res = self.create_error_data({'msg': 'Error on send email: ' + send['msg'], 'cod_resp': '617'}, 305)
                    return
                res = self.create_success_msg('Usuario aprobado: mail enviado', 200)

            # Rechazamos el documento
            elif data['status'] == 'RJ':
                conn = mysql.connector.connect(
                                    user=CONFIG['user'],
                                    password=CONFIG['password'],
                                    host=CONFIG['host'],
                                    database=CONFIG['dbname'],
                                    port=CONFIG['port'])
                cursor = conn.cursor()  
                sql= "SELECT uave.* FROM usr_auto_verification_events uave WHERE session_id = %s AND error = %s"
                error = 1
                datasql=(session_id, error)
                cursor.execute(sql, datasql)
                select_event = cursor.fetchone()
                conn.commit()
                if select_event[2] == "watchlists" or "document-reading":
                    reason_rej = 15
                elif select_event[2] == "facematch" or "selfie":
                    reason_rej = 11
                elif select_event[2] == "alteration-detection":
                    reason_rej = 16
                else:
                    reason_rej = 40
                cursor.close()
                sql2= f"SELECT rrj.*, usr.email FROM reason_rejection rrj join usr_user usr on usr.id_user = {data['user_id']} where id = {reason_rej}"
                cursor = conn.cursor()
                cursor.execute(sql2)
                select_reason = cursor.fetchone()
                conn.commit()
                cursor.close()
                conn.close()
                template = self.structure_mail_verificationReject(select_reason)
                if not template['success']:
                    res = (self.create_error_data({'msg': 'Error on template: ' + template['msg'], 'cod_resp': '615'}, 304))
                    return

                send = self.send_mail(select_query[2], template['datos'])
                if not send['success']:
                    res = (self.create_error_data({'msg': 'Error on send email: ' + send['msg'], 'cod_resp': '617'}, 305))
                    return
                res = (self.create_success_msg('Usuario rechazado: mail enviado', 200))
            
            elif data['status'] == 'RN':
                template = self.structure_mail_reviewNeeded(select_query[1], mati_url)
                if not template['success']:
                    res = self.create_error_data({'msg': 'Error on template: ' + template['msg'], 'cod_resp': '615'}, 304)
                    return
                send = self.send_mail(MAIL_ADMIN, template['datos'])
                if not send['success']:
                    res = self.create_error_data({'msg': 'Error on send email: ' + send['msg'], 'cod_resp': '617'}, 305)
                    return
                res = self.create_success_msg('Review needed: mail enviado', 200)
            
        except Exception as e:
            print(res, e)
            res = (self.create_error_data({'msg': 'Exception on update_document: ' + str(e), 'cod_resp': 602}, 500))
            if cursor:
                cursor.close()
                self.__conn.close()
        finally:
            print(res)
            return res

    def send_mail(self, to_email,template_dict,to_name=None,reply_to=None,reply_name=None,cc=None,ccname=None,bcc=None,bccname=None):
        """     
            # parametros:  to_email(email aquien se enviara correo),template_dict(email_template)
            # Descripcion: Realiza conexion con sendgrid y premite enviar correo 
                            con los datos ingresado por parametro
        """
        #   API_KEY de la cuenta con sendgrid

        try:
            API_KEY_SENDGRID = config.Config.API_KEY_SENDGRID
            #   Conectando API_KEY con serdgrid
            sg = sendgrid.SendGridAPIClient(apikey =API_KEY_SENDGRID)
            #   Preparando data para sendgrid
            data = {
                "headers": {},
                "mail_settings": {
                    "footer": {
                        "enable": True,
                        "html":template_dict['social_network']+template_dict['footer'],
                        "text": ""
                    }
                },
                "personalizations": [
                {
                "to": [
                    {
                    "email": to_email
                    }
                ],
                "subject": template_dict['subject']
                }
                ],
                "from": {
                "email": "noreplay@"+str(template_dict['company_name'].lower())+".com",
                "name": template_dict['company_name']
                },
                "content": [
                {
                "type": "text/html",
                "value": template_dict['message']
                }
                ]
                }

            if to_name!=None:
                data["personalizations"][0]["to"][0]["name"] = to_name
            if reply_to!=None:
                data["reply_to"]={"email":reply_to,"name":reply_name}

            if cc!=None:
                data["personalizations"][0]["cc"] = [{"email":cc,"name":ccname}]
            if bcc!=None:
                data["mail_settings"]["bcc"]= {"email":bcc,"enable":True}
                data["personalizations"][0]["bcc"] = [{"email":bcc,"name":bccname}]

            #   Validacion de campos
            if to_email!='' or to_email is not None:
                if template_dict['subject'] !='' or template_dict['subject'] is not None:
                    if template_dict['message']!='' or template_dict['message'] is not None:
                        if template_dict['footer']!='' or template_dict['footer'] is not None:
                            if template_dict['social_network']!='' or template_dict['social_network'] is not None:
                                # sendgrid envia email
                                response = sg.client.mail.send.post(request_body = data)
                                if response.status_code == 202:
                                    res_all = self.create_success_msg('Mail was sent correctly.',200)
                                else:
                                    res_all = self.create_error_msg('Fail in sending mail.',201)
                            else:
                                res_all = self.create_error_msg('Social_network can not be empty.',203)
                        else:
                            res_all = self.create_error_msg('Footer can not be empty.',204)
                    else:
                        res_all = self.create_error_msg('Content can not be empty .',205)
                else:
                    res_all = self.create_error_msg('Subject can not be empty .',206)
            else:
                res_all = self.create_error_msg('Email can not be empty .',207)
        except Exception as e:
            res_all =  self.create_error_msg(str(e)+' Exception on send_mail', 500)
        finally:
            return res_all

    def extrae_template_email(self, lang_id,origin,type_email):
        try:
            res = "Error Template Email"
            sql= f"SELECT * FROM email_templates WHERE lang_id = {lang_id} AND origin = {origin} AND type_email= {type_email}"
            
            email_temp = self.execute_query_dict(sql)
            if email_temp['code'] == 200 and email_temp['data']:
                res = self.create_success_data(email_temp['data'][0],email_temp['code'])
            else:
                res = self.create_error_msg('Error in connection with database: '+str(email_temp['data']),602) 
        except Exception as e:
            print(res, e)
            res = self.create_error_msg(str(e),602)
        finally:
            return res

    def structure_mail_verificationComplete(self, username):
        """ 
            @Descripcion: Extrae email_template de bd bitinka y retorna template en json
        """
        try:
            res = "Error Verification Complete"
            origin, type_email, lang_id, company_name = 3, 24, 2, 'Blockzy'

            # Extrae template
            email_temp = self.extrae_template_email(lang_id,origin,type_email)
            if email_temp['success'] == False:
                res = self.create_error_msg('No template found in email_templates table',500)
            else:
                data={
                    'subject':email_temp['datos']['subject'],
                    'footer' :email_temp['datos']['footer'].replace('"',"'").replace("\n"," "),
                    'social_network' :email_temp['datos']['social_network'].replace('"',"'").replace("\n"," "),
                    'message' : email_temp['datos']['message'].replace('"',"'")\
                        .replace("\n"," ").replace("##LOGO##",email_temp['datos']['logo'])\
                        .replace("##RRSS## ##FOOTER##"," ")\
                        .replace("##USERNAME##",username),
                    'company_name':company_name
                }
                res = self.create_success_data(data)
        except Exception as e:
            print(res, e)
            res = self.create_error_msg(str(e))
        finally:
            return res
    
    def structure_mail_verificationReject(self, reason):
        """ 
            @param:   param_dict = {"id_user":7,"username":"dcarrillo","ip":"190.8.144.82"}
                            dict_query = {"language":1,"platform":"bitinka"}
            @Descripcion: Extrae email_template de bd bitinka y retorna template en json
        """
        try:
            res = "Error Verification Reject"
            origin, type_email, lang_id, company_name = 3, 21, 2, 'Blockzy'

            #Armar el mensaje
            razon = reason[1].split("|")
            descripcion = reason[2].split("|")
            mensaje = f"""Este documento no cumple con nuestras políticas, por lo cual ha sido <strong>Rechazado</strong>.<br>
            <strong>Motivo: </strong>{razon[0]}<br>
            <strong>Descripcion: </strong>{descripcion[0]}<br><br>
            This document does not comply with our policies, for which reason it has been <strong>Rejected</strong>.<br>
            <strong>Reason: </strong>{razon[1]}<br>
            <strong>Description: </strong>{descripcion[1]}
            """
            
            # Extrae template
            email_temp = self.extrae_template_email(lang_id,origin,type_email)
            if email_temp['success'] == False:
                res = self.create_error_msg('No template found in email_templates table',500)
                return
            else:
                data={
                    'subject':email_temp['datos']['subject'],
                    'footer' :email_temp['datos']['footer'].replace('"',"'").replace("\n"," "),
                    'social_network' :email_temp['datos']['social_network'].replace('"',"'").replace("\n"," "),
                    'message' : email_temp['datos']['message'].replace('"',"'")\
                        .replace("\n"," ").replace("##LOGO##",email_temp['datos']['logo'])\
                        .replace("##RRSS## ##FOOTER##"," ").replace("##DOCUMENTO##"," ")\
                        .replace("##MSJ##",mensaje),
                    'company_name':company_name
                }
                res = self.create_success_data(data)
        except Exception as e:
            print(res, e)
            res = self.create_error_msg(str(e))
        finally:
            return res

    def structure_mail_reviewNeeded(self, username, mati_url):
        """ 
            @Descripcion: Extrae email_template de bd bitinka y retorna template en json
        """
        try:
            res = "Error Review Needed"
            origin, type_email, lang_id, company_name = 3, 37, 2, 'Blockzy'

            # Extrae template
            email_temp = self.extrae_template_email(lang_id,origin,type_email)
            if email_temp['success'] == False:
                res = self.create_error_msg('No template found in email_templates table',500)
            else:
                data={
                    'subject':email_temp['datos']['subject'],
                    'footer' :email_temp['datos']['footer'].replace('"',"'").replace("\n"," "),
                    'social_network' :email_temp['datos']['social_network'].replace('"',"'").replace("\n"," "),
                    'message' : email_temp['datos']['message'].replace('"',"'")\
                        .replace("\n"," ").replace("##LOGO##",email_temp['datos']['logo'])\
                        .replace("##RRSS## ##FOOTER##"," ")\
                        .replace("##USERNAME##",username).replace("##MATIURL##",mati_url),
                    'company_name':company_name
                }
                res = self.create_success_data(data)
        except Exception as e:
            print(res, e)
            res = self.create_error_msg(str(e))
        finally:
            return res

    @staticmethod
    def create_error_msg(msg,code_error=None):
        """     
            # parametros:  mensaje tipo str
            # Descripcion: Funcion retorna diccionario con success False
        """
        data  = {
            'success': False, 
            'msg': msg,
            'code_error':code_error
        } 
        return data 

    @staticmethod
    def create_error_data(msg,code_error=None):
        """     
            # parametros:  mensaje tipo str
            # Descripcion: Funcion retorna diccionario con success False
        """
        data  = {
            'success': False, 
            'datos': msg,
            'code_error':code_error
        } 
        return data 

    @staticmethod
    def create_success_data(data,code=None):
        """     
            # parametros:  data tipo dict o list
            # Descripcion: Funcion retorna diccionario con data success True
        """
        response = {
            'success': True, 
            'datos': data,
            'code':code
        }
        return response 

    @staticmethod
    def create_success_msg(msg,code=None):
        """     
            # parametros:  mensaje tipo str
            # Descripcion: Funcion retorna diccionario con success True
        """
        response = {
            'success': True, 
            'msg': msg,
            'code':code
        }
        return response 
