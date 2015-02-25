/*
 * Cryptography workers for x509 and RSA keys validation.
 *
 * Copyright (C) 2014 by deipi.com LLC. All rights reserved.
 *
 * Contributing author: German Mendez Bravo (german.mb@deipi.com)
 */

// BEGIN monkeypatch X509 (add hex2dno)

X509.Z2date = function(z) {
	var i = 0,
		date = z.replace(/([0-9]{2})/g, function() {
			i++;
			if (i == 1) {
				return (parseInt(arguments[1], 10) + 2000) + '-';
			}
			if (i < 3) {
				return arguments[1] + '-';
			}
			if (i == 3) {
				return arguments[1] + 'T';
			}
			if (i < 6) {
				return arguments[1] + ':';
			}
			return arguments[1];
		});
	if (i == 6) {
		return new Date(date);
	}
};

X509.hex2string = function(h) {
	return h.replace(/([0-9A-Fa-f]{2})/g, function() {
		return String.fromCharCode(parseInt(arguments[1], 16));
	});
};

X509.hex2dno = function(hDN) {
	var o = {};
	var a = ASN1HEX.getPosArrayOfChildren_AtObj(hDN, 0);
	for (var i = 0; i < a.length; i++) {
		var hRDN = ASN1HEX.getHexOfTLV_AtObj(hDN, a[i]);
		var tv = X509.hex2rdno(hRDN);
		o[tv[0]] = tv[1];
	}
	return o;
};

X509.hex2rdno = function(hRDN) {
	var hType = ASN1HEX.getDecendantHexTLVByNthList(hRDN, 0, [0, 0]);
	var hValueType = ASN1HEX.getDecendantHexTLVByNthList(hRDN, 0, [0, 1]).substring(0, 2);
	var hValue = ASN1HEX.getDecendantHexVByNthList(hRDN, 0, [0, 1]);
	var type = "";
	var value = "";
	try {
		type = X509.DN_ATTRHEX[hType] || hType;
	} catch (ex) {
		type = hType;
	}
	if (hValueType === '0c') {
		// UTF8
		hValue = hValue.replace(/(..)/g, "%$1");
		value = decodeURIComponent(hValue);
	} else {
		for (var i = 0; i < hValue.length; i += 2) {
			value += String.fromCharCode(parseInt(hValue.substr(i, 2), 16));
		}
	}
	return [type, value];
};

X509.DN_ATTRHEX = {
	"0603550406": "countryName", // C
	"060355040a": "organizationName",  // O
	"060355040b": "organizationalUnitName",  // OU
	"0603550403": "commonName",  // CN
	"0603550405": "serialNumber",  // SN
	"0603550408": "stateOrProvinceName",  // ST
	"0603550407": "localityName",  // L
	"0603550429": "name",
	"0603550411": "postalCode",
	"0603550409": "streetAddress",
	"060355042d": "uniqueIdentifier",
	"06092a864886f70d010901": "emailAddress",
	"06092a864886f70d010902": "unstructuredName"
};

KEYUTIL.getRSAKeyFromData = function(key_data) {
	if (!key_data) return;
	var key = new RSAKey();
	key.n = new BigInteger(key_data.n);
	key.e = key_data.e;
	key.d = new BigInteger(key_data.d);
	key.p = new BigInteger(key_data.p);
	key.q = new BigInteger(key_data.q);
	key.dmp1 = new BigInteger(key_data.dmp1);
	key.dmq1 = new BigInteger(key_data.dmq1);
	key.coeff = new BigInteger(key_data.coeff);
	key.isPrivate = key_data.isPrivate;
	return key;
};

// END monkeypatch

keychains = {};

(function() {
	"use strict";

	function serialize_data(key) {
		if (key) {
			return {
				n: key.n.toString(),
				e: key.e,
				d: key.d.toString(),
				p: key.p.toString(),
				q: key.q.toString(),
				dmp1: key.dmp1.toString(),
				dmq1: key.dmq1.toString(),
				coeff: key.coeff.toString(),
				isPrivate: key.isPrivate
			};
		}
	}

	var _keychains_cache = {};

	function initialize(app, keychain) {
		var self = null;//_keychains_cache[app]

		if (!self) {
			self = _keychains_cache[app] = {
				keychain: keychain || {
					current: {}
				}
			};
		}

		if (!self.keychain) {
			self.keychain = keychain || {
				current: {}
			};
		}

		if (!self.keychain.current) {
			self.keychain.current = {};
		}

		var current = self.keychain.current,
			current_valid = self.keychain[current.serial];
		if (current_valid !== undefined &&
			current_valid.cer_pem === current.cer_pem &&
			current_valid.key_pem === current.key_pem &&
			current_valid.passphrase === current.passphrase) {
			current = current_valid;
		}

		load_keyring(self, current);

		return self;
	}

	function load_keyring(self, keyring) {
		self.cer = undefined;
		self.key = undefined;
		self.valid = keyring.valid;
		self.cer_pem = keyring.cer_pem;
		self.key_pem = keyring.key_pem;
		self.passphrase = keyring.passphrase;
		self.key_data = keyring.key_data;
		self.serial = keyring.serial;
		self.issuer = keyring.issuer;
		self.notBefore = keyring.notBefore;
		self.notAfter = keyring.notAfter;
		self.subject = keyring.subject;
		self.sha1 = keyring.sha1;
		// console.debug("Loaded keyring:", keyring);
	}

	function save_keyring(self) {
		var keyring = {
			valid: self.valid,
			cer_pem: self.cer_pem,
			key_pem: self.key_pem,
			passphrase: self.passphrase,
			key_data: self.key_data,
			serial: self.serial,
			issuer: self.issuer,
			notBefore: self.notBefore,
			notAfter: self.notAfter,
			subject: self.subject,
			sha1: self.sha1
		};
		// console.debug("Saved keyring:", keyring);
		return keyring;
	}

	function verify(self) {
		// console.log("Verifying...");

		var cer_status = try_cer(self),
			key_status = try_key(self);

		if (cer_status === false) {
			// console.log("Invalid certificate!");
			return false;
		}

		if (key_status === false) {
			// console.log("Invalid key!");
			return false;
		}

		if (self.cer && self.key) {
			if (!self.valid) {
				var keyring = save_keyring(self);
				// console.log("Testing...", keyring);
				// New keychain or changed. Try signing:
				var sMsg = "Signature Test",
					hSig = self.key.signString(sMsg, 'sha1'),
					isValid = self.cer.subjectPublicKeyRSA.verifyString(sMsg, hSig);
				self.valid = keyring.valid = isValid;
				self.keychain.current = keyring;
				if (isValid) {
					self.keychain[self.serial] = keyring;
				}
			}
			if (self.valid) {
				// console.log("Valid signing!", self.serial);
			} else {
				// console.log("Invalid signing!", self.serial);
				throw "Invalid signing!";
			}
			return true;
		}

		// console.log((!self.cer && !self.key) ? "No loaded key and certificate." : !self.cer ? "No loaded certificate." : "No loaded key.");

		if (self.cer_pem !== undefined || self.key_pem !== undefined || self.passphrase) {
			return null;
		}
	}


	function try_passphrase(self, value) {
		var status = null;

		if (value !== undefined) {
			if (self.passphrase != value) {
				self.key = undefined;
				self.valid = undefined;
				self.passphrase = value;
				self.key_data = undefined;
			}
		}

		if (self.passphrase !== undefined) {

			self.keychain.current = save_keyring(self);
			// console.log("Passphrase loaded:", self.passphrase);

			status = verify(self);

			return status;
		}
	}

	function try_cer(self, base64Content) {
		var status = null,
			old = save_keyring(self),
			old_cer = self.cer;

		if (base64Content !== undefined) {
			if (self.cer_pem !== base64Content) {
				self.cer = undefined;
				self.valid = undefined;
				self.cer_pem = base64Content;
				self.serial = undefined;
				self.issuer = undefined;
				self.notBefore = undefined;
				self.notAfter = undefined;
				self.subject = undefined;
				self.sha1 = undefined;
			}
		}

		if (self.cer_pem !== undefined && !self.cer) {
			try {
				X509.getPublicKeyFromCertPEM(self.cer_pem);
				self.cer = new X509();
				self.cer.readCertPEM(self.cer_pem);
			} catch (ex) {
				// console.error(ex, self.cer_pem);
				load_keyring(self, old);
				self.cer = old_cer;
				return false;
			}

			self.serial = X509.hex2string(self.cer.getSerialNumberHex());
			self.issuer = X509.hex2dno(self.cer.getIssuerHex());
			self.notBefore = X509.Z2date(self.cer.getNotBefore());
			self.notAfter = X509.Z2date(self.cer.getNotAfter());
			self.subject = X509.hex2dno(self.cer.getSubjectHex());
			self.sha1 = KJUR.crypto.Util.hashString(self.cer.hex, 'sha1');

			self.keychain.current = save_keyring(self);
			// console.log("[x509] Certificate loaded:", self.keychain.current);

			if (base64Content) {
				status = verify(self);
			} else {
				status = true;
			}

			return status;
		}
	}

	function try_key(self, base64Content) {
		var status = null,
			old = save_keyring(self),
			old_key = self.key;

		if (base64Content !== undefined) {
			if (self.key_pem !== base64Content) {
				self.key = undefined;
				self.valid = undefined;
				self.key_pem = base64Content;
				self.key_data = undefined;
			}
		}

		if (self.key_pem !== undefined && !self.key) {
			if (self.passphrase) {
				try {
					if (self.key_data) {
						self.key = KEYUTIL.getRSAKeyFromData(self.key_data);
					} else {
						try {
							self.key = PKCS5PKEY.getRSAKeyFromEncryptedPKCS8PEM(self.key_pem, self.passphrase);
						} catch (ex) {
							if (self.passphrase == self.passphrase.toUpperCase()) {
								self.key = PKCS5PKEY.getRSAKeyFromEncryptedPKCS8PEM(self.key_pem, self.passphrase.toLowerCase());
							} else if (self.passphrase == self.passphrase.toLowerCase()) {
								self.key = PKCS5PKEY.getRSAKeyFromEncryptedPKCS8PEM(self.key_pem, self.passphrase.toUpperCase());
							} else {
								throw ex;
							}
						}
					}
				} catch (ex) {
					// console.error(ex, self.key_pem, self.passphrase);
					load_keyring(self, old);
					self.key = old_key;
					return false;
				}

				self.key_data = serialize_data(self.key);
			}

			self.keychain.current = save_keyring(self);
			// console.log("[RSA] Key loaded:", self.keychain.current.key_data || self.keychain.current.key_pem);

			if (self.passphrase) {
				if (base64Content) {
					status = verify(self);
				} else {
					status = true;
				}
			}

			return status;
		}
	}

	workers.pem_validation = function(app, base64Content, keychain) {
		try {
			var self = initialize(app, keychain),
				is_certificate,
				valid = true,
				exception,
				status;

			if (base64Content) {
				if (base64Content.substr(0, 2) != 'MI') {
					base64Content = atob(base64Content);
					if (base64Content.indexOf("CERTIFICATE") != -1) {
						is_certificate = true;
					} else if(base64Content.indexOf("PRIVATE KEY") != -1) {
						is_certificate = false;
					}
				}

				if (is_certificate !== false) {
					status = try_cer(self, base64Content);
					if (status === false) {
						if (is_certificate === undefined) {
							base64Content = '-----BEGIN ENCRYPTED PRIVATE KEY-----\n' + base64Content + '\n-----END ENCRYPTED PRIVATE KEY-----\n';
							is_certificate = false;
						}
					}
				}

				if (is_certificate === false) {
					status = try_key(self, base64Content);
				}
			}

			if (status === false) {
				valid = false;
			}
			return [valid, exception, status, self.keychain];
		} catch (ex) {
			// console.error(ex);
			return [false, ex, false, self.keychain || keychain];
		}
	};

	workers.passphrase_validation = function(app, value, keychain) {
		try {
			var self = initialize(app, keychain),
				valid = true,
				exception,
				status;

			status = try_passphrase(self, value);

			if (status === false) {
				valid = false;
			}
			return [valid, exception, status, self.keychain];
		} catch (ex) {
			// console.error(ex);
			return [false, ex, false, self.keychain || keychain];
		}
	};

	workers.signature = function(app, sMsg, hashed, keychain) {
		var self = initialize(app, keychain);

		if (self.valid) {
			var cer_status = try_cer(self),
				key_status = try_key(self);

			if (cer_status === false) {
				return [false, null];
			}

			if (key_status === false) {
				return [false, null];
			}

			var hSig, isValid;
			if (hashed) {
				hSig = self.key.signWithMessageHash(sMsg, 'sha1');
				isValid = self.cer.subjectPublicKeyRSA.verifyWithMessageHash(sMsg, hSig);
			} else {
				sMsg = sMsg.replace(/\{\{\s*serialNumber\s*\}\}/g, self.serial);
				hSig = self.key.signString(sMsg, 'sha1');
				isValid = self.cer.subjectPublicKeyRSA.verifyString(sMsg, hSig);
			}

			if (!isValid) {
				hsig = null;
			}

			return [isValid, hSig];
		}

		return [false, null];
	};
})();
