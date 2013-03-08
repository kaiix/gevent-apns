CERT=apns_cert
CAFILE=server-ca-cert

pem:
	openssl pkcs12 -in $(CERT).p12 -out $(CERT).pem -nodes

connection:
	openssl s_client -connect gateway.sandbox.push.apple.com:2195 -cert $(CERT).pem -debug -showcerts -CAfile $(CAFILE).pem
