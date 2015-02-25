(function() {
	YAHOO = {
		lang: {
			extend: function(subc, superc, overrides) {
				if (!superc||!subc) {
					throw new Error("extend failed, please check that " +
									"all dependencies are included.");
				}
				var F = function() {}, i;
				F.prototype=superc.prototype;
				subc.prototype=new F();
				subc.prototype.constructor=subc;
				subc.superclass=superc.prototype;
				if (superc.prototype.constructor == Object.prototype.constructor) {
					superc.prototype.constructor=superc;
				}

				if (overrides) {
					for (i in overrides) {
						if (Object.prototype.hasOwnProperty(overrides, i)) {
							subc.prototype[i]=overrides[i];
						}
					}
				}
			}
		}
	};
})();