# -*- coding: UTF-8 -*-
import os

class Config():
    '''
        This is the config class.
        In this section you have to put all the static values for the variables needed.
    '''

    # Sendgrid API_KEY
    API_KEY_SENDGRID = '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'
    
    def __init__(self):
        '''
            This is the contructor for the config class
            :var proxy: This is the proxy dict to be used on the HTTP Requests:
                proxy example:
                'proxy':{
                        'https': '181.177.76.68:3199',
                        'http': '181.177.76.68:3199'
                        }
            :var log_base_dir: Path to create the log file
            :var user: Database user.
            :var password: Database password.
            :var host: Database host ip address.
            :var database: Database name.
        '''
        self.__RootDir = os.path.dirname(os.path.abspath(__file__))
        self.__configDict = {
            'ip_allowed':[],
            'user': 'fbattan',
            'password': 'dPgTb3ywpVmmvHkzqmNV',
            'host': '192.168.9.10',
            'dbname': 'blockzy',
            'port':'1987'
        }


    @property
    def configDict(self):
        '''
            This is the configDict getter method
        :return: configDict attribute value.
        '''
        return self.__configDict