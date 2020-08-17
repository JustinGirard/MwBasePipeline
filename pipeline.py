import sys,json
sys.path.append('../')

import datetime, pandas as pd
from DataPipeline.DataLake import DataLake
from DataPipeline.Model import Model
from DataPipeline.Request import Request
from DataPipeline.Task import Task #TBD Scheduled Task support
from DataPipeline.Test import Test #TBD Unit Test support

from processingNetwork.ProcessingNode import ProcessingNode
from processingNetwork.ProcessingNetwork import ProcessingNetwork
import json

class ExamplePipelineTest(Test):
    '''
        JG: THIS IS IN DEVELOPMENT. LOOKING AT GENERALIZING PIPELINES.
    '''
    def test_assert_true():
        feature = {'api_key':'fbakfajkf',}
        settings = {}        
        ### Do some work
        self.assertTrue(True==True)

class ExampleDownloadTask(Task):
    '''
        JG: THIS IS IN DEVELOPMENT. LOOKING AT GENERALIZING TASKS.
    '''
    def do_input(self,feature,settings):
        # CHECK  do_schedule, then,... do_task 
        # TODO (for JG) , Enforce Schedule and create executed task log
        return self.do_task(feature,settings)
        
    def do_task(self,feature,settings):
        '''
            This function gets called with feature['action'] = <VALUE> at the appropriate times.
            Do any event work in this method.
        '''
        # When we are called, we just download and save a historical snapshot with todays date.
        import os
        import json
        import urllib.request
        import datetime
        nw = datetime.datetime.utcnow()
        if not 'action' in feature or feature['action']== None:
            feature['action'] = 'manual'
        if not 'year' in feature or feature['year']== None:
            feature['year'] = nw.year
        if not 'month' in feature or feature['month']== None:
            feature['month'] = nw.month
        if not 'day' in feature or feature['day']== None:
            feature['day'] = nw.day
        feature['datetime'] = datetime.datetime(year=feature['year'],month=feature['month'],day=feature['day'])
        req_date = feature['datetime'] + datetime.timedelta(days=1)
        feature['invocation_datetime'] = datetime.datetime.utcnow()
        
        import time
        import datetime
        unixtime = time.mktime(req_date.timetuple())        
        feature['type'] = 'test_finance_request'
        url = "https://min-api.cryptocompare.com/data/v2/histohour?fsym=ETH&tsym=BTC&limit=24&aggregate=1&toTs="+str(unixtime)
        headers = { }

        request = urllib.request.Request(url=url, headers=headers)
        response = urllib.request.urlopen(request, timeout=5)
        responseBody = response.read().decode("utf-8")
        jsonResponse = json.loads(responseBody)
        #print(json.dumps(jsonResponse, sort_keys=True, indent=4))
        #import pandas as pd
        #d.DataFrame(jsonResponse["Data"]['Data'])        
        dat = jsonResponse["Data"]['Data']        
        
        
        # Insert data into the DataLake. 
        # We use the MwRequest() interface to use the data lake for many reasons....
        # 1. api_key allows for developer accounts to be created with different developer permissions
        # 2. Coding in this way allows this Task to be moved to other processing locations (into other packages / products)
        # 3. Additional errors in fields are searched for and caught by the MwRequest class.
        # 4. If the data lake for the query_id changes, then the whole code base will instantly point to the new data lake
        # 5... there are other good reasons (but 5 is enough)
        # (!) In general, it is possible to "Bypass" MwRequest() to create a DataLake() directly. Doing so instantly loses the 
        # (1-4) above, with the gain of slight immediate ease of use. It is hard to reccomend against the course of action with enough fervency.
        # In general, all inter-package calls should be funneled 
        # through the MwRequest object to ensure adoption of a 'microservices' oriented architecture.
        # https://microservices.io/patterns/microservices.html (an example of the paradigm)
        req = MwRequest() 
        result = req.do_input({'query_id':'datalake_insert',
                              'api_key':'API_USER_123',
                               'query':{'key':'crypto_compare_'+str(feature['year'])+'_'+str(feature['month'])+'_'+str(feature['day']),
                                        'meta':feature,
                                        'data':dat},},{})
        if 'error' in result:
            print(result['error'])
        else:
            print(result)            
        return True
        
    def get_schedule(self):
        '''
        TODO: (JG) Will implement automatic task scheduling and execution.
        Define this jobs schedule, and what arguments get passed to the task upon each schedule invocation
        
        '''
        events = [
                {'event':'initalize','arguments':{'action':'initialize'}},
                {'event':'teardown','arguments':{'action':'teardown'}},
                {'event':'daily','arguments':{'action':'1'}},
                {'event':'hourly','arguments':{'action':'2'}},
                {'event':'weekly','arguments':{'action':'3'}},
                {'event':'monday','arguments':{'action':'4'}},
                {'event':'tuesday','arguments':{'action':'5'}},
                {'event':'wednesday','arguments':{'action':'6'}},
                {'event':'thursday','arguments':{'action':'7'}},
                {'event':'friday','arguments':{'action':'8'}},
                {'event':'schedule','arguments':{'action':'9'},
                 'time_start':datetime.datetime.utcnow(),'time_interval':datetime.timedelta(days=30)},
                 ]
    
    
class MwDataLake(DataLake):

    def get_json(self,obj):
        return json.loads(
        json.dumps(obj, default=lambda o: getattr(o, '__dict__', str(o)))
      )
    def do_insert(self,feature,settings):
        # Imports the Google Cloud client library
        from google.cloud import datastore
        import os
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"]=settings['GOOGLE_APPLICATION_CREDENTIALS']
        # Instantiates a client
        datastore_client = datastore.Client()

        # The kind for the new entity
        kind = settings['data_lake_id']
        # The name/ID for the new entity
        name = feature['key']
        # The Cloud Datastore key for the new entity
        task_key = datastore_client.key(kind, name)

        # Prepares the new entity
        task = datastore.Entity(key=task_key)
        for k in feature['meta']:
            task[k] = feature['meta'][k]

        task['__data'] = feature['data']

        # Saves the entity
        datastore_client.put(task)

        return 'Saved {}: {}'.format(task.key.name, str(feature['meta']))

    def do_find(self,feature,settings):
        '''
        Implementation of a find implementation for the google datastore. Must return a nested dictionary.

        '''
        from google.cloud import datastore
        for k in feature:
            assert k in ['key','meta','query']

        #
        # Implementation specific
        #
        # 
        #
        if 'key' in feature and not feature['key'] == None: #Handle key lookup 
            import os
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"]=settings['GOOGLE_APPLICATION_CREDENTIALS']
            datastore_client = datastore.Client()

            query = datastore_client.query(kind= settings['data_lake_id'])
            query.key_filter(datastore.key.Key( settings['data_lake_id'], feature['key'],project=settings['GOOGLE_PROJECT_ID']))
            result = query.fetch()
            return self.get_json(list(result))

        if 'meta' in feature and not  feature['meta'] == None: #Handle Meta seacrh
            import os
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"]=settings['GOOGLE_APPLICATION_CREDENTIALS']
            datastore_client = datastore.Client()

            query = datastore_client.query(kind= settings['data_lake_id'])
            for k in feature['meta']:
                query.add_filter(k, '=', feature['meta'][k])
            result = query.fetch()
            return self.get_json(list(result))

        if 'query' in feature and not  feature['query'] == None: #Handle Query
            raise Exception("query is not implemented, but it should be eventually! ")
            pass

    def do_delete(self,feature,settings):
        raise Exception("Delete is not supported on this kind of object")
        pass # Unimplemented. Implement to support delete
    
    
class MwRequest(Request):
    '''
    A request is a mapping function that transforms a data request into resulting json data. It considers access permissions, and other issues pertaning to HTTP/HTTPS encoding. Queries supported:
    1) DataLake Queries - Get and dump data into a data lake
    2) Model Queries - TBD (tables, views, functions, metrics, data methods)
    3) System Instrctions - Deploy, and access any hard coded queries
    3) Task Queries - Trigger and list scheduled tasks
    
    '''
    def pipeline_globals(self):
        return globals()
    
    def get_registry(self):
        '''
            The registry maps functions from within different modules into the request system. This allows the kinds of requests to be augmented. Note that the registry is all text. This means that it can be stored in json, configured within version control, always be human readable, and can even be eventually be stored within a database. 
        '''
        sys = System()        
        #presently, we just send back a hard-coded registry
        return sys.get_setting('api_registry')
    
    def get_api_keys(self,request):
        '''
            List of allowed users. Logic related to permissions and other user-based authentication can go here. Right now we just return registered users. In general this is a good place to do any logic related to user permissions related to real-time access. The request is provided, so if, for example, permissions differ based on a type of query, that logic can be included here.
        '''
        sys = System()
        return sys.get_setting('api_users')
    
    def access_log(self,feature,user):
        '''
        If needed, do something with the requested query. By default, we do nothing.
        '''
        #print("PROCESSING... "+ str(feature) + ' for '+ str(user))
        pass

    
class System(ProcessingNode):
    def get_setting(self,key):
        '''
        get_setting can be over ridden to handle settins in varios ways. In this example we just use a single method
        to contain all system dependencies.
        '''
        datalake_settings = {"GOOGLE_APPLICATION_CREDENTIALS":"creds.json", 
                            "GOOGLE_PROJECT_ID":'mwdatapipelineex',
                             "data_lake_id":'row',           
                             }
        
        registry = {
                'task_update_testdata':{
                                'class':'ExampleDownloadTask', 
                                'query_id':'task_update_testdata',
                                'method':'do_input', 
                                'arguments':{},
                                'settings':{}
                                },
                'datalake_insert':{
                                'class':'MwDataLake', 
                                'query_id':'datalake_insert',
                                'method':'do_input', 
                                'arguments':{'qtype':'do_insert'},
                                'settings':datalake_settings
                                },
                'datalake_find':{
                                'class':'MwDataLake', 
                                'query_id':'datalake_find',
                                'method':'do_input', 
                                'arguments':{'qtype':'do_find'},
                                'settings':datalake_settings
                                }
                   }     
        users = {'API_USER_123':{'user_id':'brian123',
                                'user_meta_data':'meta_123'}}
        
        settings = {}
        settings['datalake_settings'] = datalake_settings
        settings['api_registry'] = registry
        settings['api_users'] = users
        return settings[key]
    
    def get_request_class():
        return MwRequest
    
    def set_setting(self,key):
        pass
    
    
    
#class APIRequest():
#    '''
#    A General API request. This is used both locally (within plugin), and externally (by third parties) to access data and services between modules.
#    '''
#    def query(query,location=None):
        
