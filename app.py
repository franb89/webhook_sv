from flask import Flask, request, abort
import requests
import config
import datalayer

Config=config.Config().configDict
app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
	"""
		Recibe el webhook de la app de mati
		Ejemplo:
		{ "metadata": {
			"user_id": "52321"
			},
		  "resource": "https://api.getmati.com/v2/verifications/6081c5a5a908fc001bda4915",
		  "deviceFingerprint": {
			"ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0",
			"browser": {
			  "name": "Firefox",
			  "version": "88.0",
			  "major": "88"
			},
			"engine": {
			  "name": "Gecko",
			  "version": "88.0"
			},
			"os": {
			  "name": "Windows",
			  "version": "10"
			},
			"cpu": {
			  "architecture": "amd64"
			},
			"ip": "181.199.146.54",
			"app": {
			  "platform": "web_desktop",
			  "version": "1.2.2"
			}
		  },
		  "identityStatus": "reviewNeeded",
		  "details": {
			"age": {
			  "data": 33
			},
			"isDocumentExpired": {
			  "data": {
				"national-id": false,
				"proof-of-residency": null
			  }
			}
		  },
		  "matiDashboardUrl": "https://dashboard.getmati.com/identities/6081c5a5a908fc001bda4913",
		  "status": "reviewNeeded",
		  "eventName": "verification_updated",
		  "flowId": "5fd7dcf596163a001b261c02",
		  "timestamp": "2021-04-22T19:10:23.050Z"
		}
	:return:

	usr_auto_verification_events

	event_id= int(11)PK autoincremental
	id_usr = integer(11)FK
	event_name= varchar(50)
	event_date = timestamp
	error= bool
	session_id= varchar (30)
	hook = LONGTEXT


	usr_auto_verification

	id_usr = integer(11)PK
	dashboard_url = varchar(255)
	start_verified_date = timestamp = ON INSERT CURRENT_TIMESTAMP
	complete_verified_date = timestamp = ON UPDATE CURRENT_TIMESTAMP
	verification_status = varchar(2)
	verification_ip = varchar(15)
	session_id= varchar (30)
	"""
	if request.method == "POST":
		try:
			data = request.json
			event = data['eventName']
			print(f"\n---> info: {data} <---\n\n")

			if event == "step_completed":
				if data['step']['error'] is None:
					_error = 0
				else:
					_error = 1
				info = {"id_usr": data['metadata']['user_id'],
						"event_name": data['step']['id'],
						"event_date": data['timestamp'],
						"error": _error,
						"session_id": str(data['resource']).replace("https://api.getmati.com/v2/verifications/", ""),
						"hook": data
						}		
				save_step(info['id_usr'], info['event_name'], info['event_date'], info['error'], info['session_id'], info['hook'])

			elif event == "verification_inputs_completed":
				info = {"id_usr": data['metadata']['user_id'],
						"ip": "",
						"dashboardURL": "",
						"status": "PE",
						"session_id": str(data['resource']).replace("https://api.getmati.com/v2/verifications/", "")
						}
				update_status(info['id_usr'],info['ip'],info['dashboardURL'],info['status'],info['session_id'])

			elif event == "verification_completed":
				user_id = data['metadata']['user_id']
				mati_url = data['matiDashboardUrl']
				ip_from = data['deviceFingerprint']['ip']
				identity_status = data['identityStatus']
				status = data['status']
				date = data['timestamp']
				session_id=str(data['resource']).replace("https://api.getmati.com/v2/verifications/", "")
				print("Wait until the verification proccess completes")

				if status == "reviewNeeded":
					print('review needed')
					new_status = 'RN'
					update_status(user_id,ip_from,mati_url,new_status,session_id)
					datalayer.DataLayer(Config).webhook_mail(user_id, new_status, mati_url, session_id)

				elif status == "verified":
					print("verified")
					new_status = 'AP'
					update_status(user_id,ip_from,mati_url,new_status,session_id)
					#all ok. complete level 2
					update_level(user_id,0,2)
					datalayer.DataLayer(Config).webhook_mail(user_id, new_status, mati_url, session_id)
				else:
					print('rejected')
					new_status = 'RJ'
					update_status(user_id,ip_from,mati_url,new_status,session_id)
					update_level(user_id,2,1)
					datalayer.DataLayer(Config).webhook_mail(user_id, new_status, mati_url, session_id)

			elif event == "verification_updated":
				user_id = data['metadata']['user_id']
				mati_url = data['matiDashboardUrl']
				ip_from = data['deviceFingerprint']['ip']
				identity_status = data['identityStatus']
				status = data['status']
				date = data['timestamp']
				session_id=str(data['resource']).replace("https://api.getmati.com/v2/verifications/", "")

				if identity_status == "rejected":
					print('manually rejected')
					new_status = 'RJ'
					update_status(user_id,ip_from,mati_url,new_status,session_id)
					update_level(user_id,2,1)
					datalayer.DataLayer(Config).webhook_mail(user_id, new_status, mati_url, session_id)

				elif identity_status == "verified":
					print("manually verified")
					new_status = 'AP'
					update_status(user_id,ip_from,mati_url,new_status,session_id)
					#all ok. complete level 2
					update_level(user_id,0,2)
					datalayer.DataLayer(Config).webhook_mail(user_id, new_status, mati_url, session_id)
				else:
					print('manually set for review')
					new_status = 'RN'
					update_status(user_id,ip_from,mati_url,new_status,session_id)
					datalayer.DataLayer(Config).webhook_mail(user_id, new_status, mati_url, session_id)

		except Exception as e:
			print(f"Wrong request: {e}")
	else:
		print("no es POST")
	return "ok"

def update_status(id_usr,ip,dashboard_url,status,session_id):
	try:
		print('update_status')
		datalayer.DataLayer(Config).update_ifexist_verification(id_usr,ip,dashboard_url,status,session_id)
		print('update_status for user {} ok'.format(id_usr))
	except Exception as e:
		print('Error on update_status: {}'.format(e))

def update_level(id_usr,required_level,level_completed):
	try:
		print('update_level')
		datalayer.DataLayer(Config).update_level_2(id_usr,required_level,level_completed)
		print('update_level for user {} ok'.format(id_usr))
	except Exception as e:
		print('Error on update_level: {}'.format(e))

def save_step(id_usr, event_name, event_date, error, session_id, hook):
	try:
		print("save_step")
		datalayer.DataLayer(Config).save_step(id_usr, event_name, event_date, error, session_id, hook)
		print(f"save_step for user {id_usr} ok")
	except Exception as e:
		print(f"Error on save_step: {e}")

	
if __name__ == '__main__':
	app.run(host="0.0.0.0", port=5000, debug=True)