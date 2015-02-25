var global, exports;

if ( typeof exports === 'undefined' ) {
	if(typeof(window) === 'undefined') {
		global = exports = this;
	} else {
		global = exports = window;
	}
}
