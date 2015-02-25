'use strict';
var stdin = require('./lib/get-stdin');
var autoprefixer = require('./lib/autoprefixer');

stdin(function (data) {
	var browsers = 'last 2 versions';

	var args = process.argv;
	while (args.length > 0) {
		var v = args.shift();
		switch (v) {
			case "-b":
			case "--browsers":
				browsers = args.shift().split(',');
		}
	}

	try {
		process.stdout.write(autoprefixer.apply(null, browsers).process(data).css);
	} catch (err) {
		if (/Unclosed block/.test(err.message)) {
			return console.error('Couldn\'t find any valid CSS rules. You can\'t select properties. Select a whole rule and try again.');
		}

		if (err.name === 'TypeError') {
			return console.error('Invalid CSS.');
		}

		throw err;
	}
});
