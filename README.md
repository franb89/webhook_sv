# webhook_sv
The webhooks that we send are:
Webhook 	                                                            Description
verification_started 	                      Sent at the beginning of the SDKs flow, when Mati s making a new verification record      (usually at the upload of the first ID document)

verification_inputs_completed 	              Sent when the user has uploaded all inputs via SDKs. You can use that webhook to know when to redirect the user after the verification flow on your website/App.

verification_updated 	                      Sent from your Mati dashboard manually after updating the user verification information.

verification_completed 	                      Sent once Mati is done verifying a user entirely. When you get this webhook, you should GET the 'resource' URL to get the verification data about user.

verification_expired 	                      Sent when verification is not completed after 30 minutes. It means that the user probably did not finish verification flow.

step_completed 	                              Webhook sent after each verification step is completed (liveness, face match, document-reading, alteration-detection, template-matching, watchlist)