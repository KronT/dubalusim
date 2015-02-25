// Define changes to default configuration here.
// For complete reference see:
// http://docs.ckeditor.com/#!/api/CKEDITOR.config

// The toolbar groups arrangement, optimized for a single toolbar row.
CKEDITOR.config.toolbarGroups = [
	{ name: 'document',	   groups: [ 'mode', 'document', 'doctools' ] },
	{ name: 'clipboard',   groups: [ 'clipboard', 'undo' ] },
	{ name: 'editing',     groups: [ 'find', 'selection', 'spellchecker' ] },
	{ name: 'forms' },
	{ name: 'basicstyles', groups: [ 'basicstyles', 'cleanup' ] },
	{ name: 'paragraph',   groups: [ 'list', 'indent', 'blocks', 'align', 'bidi' ] },
	{ name: 'links' },
	{ name: 'insert' },
	{ name: 'styles' },
	{ name: 'colors' },
	{ name: 'tools' },
	{ name: 'others' }
];

// The default plugins included in the basic setup define some buttons that
// are not needed in a basic editor. They are removed here.
// CKEDITOR.config.removeButtons = 'Cut,Copy,Paste,Undo,Redo,Anchor,Underline,Strike,Subscript,Superscript';
CKEDITOR.config.removeButtons = 'Cut,Copy,Paste,Anchor,Strike,Subscript,Superscript';

// Dialog windows are also simplified.
CKEDITOR.config.removeDialogTabs = 'link:advanced';

CKEDITOR.config.customConfig = null;

CKEDITOR.skinName = 'bootstrapck';

CKEDITOR.config.plugins = 'basicstyles,clipboard,enterkey,entities,floatingspace,indentlist,link,list,toolbar,undo,justify,blockquote,format';

CKEDITOR.lang.languages = {
	// es: 1,
	en: 1
};
CKEDITOR.lang.rtl = {};
