$(function() {
	var editor = null,
		editor_fnct = null,
		editor_timer = null,
		old_date = new Date() + 10000;

	function onChange(event) {
		if (editor != event.editor) {
			if (editor_fnct) editor_fnct();
			old_date = new Date() + 10000;
		} else if (new Date() > old_date) {
			return;
		}
		clearTimeout(editor_timer);
		editor = event.editor;
		editor_fnct = function() {
			var id = editor.element.getAttribute('id'),
				idx = id.substr(0, 5) === '_ped_' && id.substr(5),
				data = editor.getData();
			$.post(document.urls.page_editor, {
				idx: idx,
				data: data
			}, announce, 'json');
			editor = null;
			editor_fnct = null;
			editor_timer = null;
			old_date = new Date() + 10000;
		};
		editor_timer = setTimeout(editor_fnct, 1000);
	}

	CKEDITOR.disableAutoInline = true;
	$('[contenteditable]').each(function() {
		var editor = CKEDITOR.inline(this, {
			allowedContent: true
		});
		editor.on('change', onChange);
		// FIXME: This is an ugly fix to issue http://dev.ckeditor.com/ticket/9814
		// Chrome shows editors as read-only when they're initially not visible.
		editor.on('focus', function () {
			editor.setReadOnly(false);
		});
	});
});
