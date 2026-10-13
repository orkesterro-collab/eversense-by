/* Выбор фото из медиатеки для полей темы. */
jQuery(function ($) {
	$(document).on('click', '.ev-media-pick', function (e) {
		e.preventDefault();
		var box = $(this).closest('.ev-media');
		var frame = wp.media({ title: 'Выберите фото', button: { text: 'Использовать' }, multiple: false, library: { type: 'image' } });
		frame.on('select', function () {
			var a = frame.state().get('selection').first().toJSON();
			var url = (a.sizes && a.sizes.medium) ? a.sizes.medium.url : a.url;
			box.find('input[type=hidden]').val(a.id);
			box.find('img').attr('src', url).show();
		});
		frame.open();
	});
	$(document).on('click', '.ev-media-clear', function (e) {
		e.preventDefault();
		var box = $(this).closest('.ev-media');
		box.find('input[type=hidden]').val('');
		box.find('img').attr('src', '').hide();
	});
});
