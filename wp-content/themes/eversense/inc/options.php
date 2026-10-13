<?php
/**
 * Страница «Внешний вид → Настройки EVERSENSE»: контакты дистрибьютора,
 * соцсети, документы, видео, фото главной, ключи сервисов.
 */

defined( 'ABSPATH' ) || exit;

/** Описание полей: группа => [ключ => [подпись, тип]]. */
function ev_option_schema() {
	$langs    = ev_languages();
	$contacts = [
		'phone'   => [ 'Телефон', 'text' ],
		'phone_2' => [ 'Второй телефон', 'text' ],
		'email'   => [ 'E-mail', 'text' ],
	];
	foreach ( [ 'company' => 'Название компании', 'requisites' => 'Реквизиты (УНП, адрес)', 'office' => 'Адрес офиса', 'warehouse' => 'Адрес склада', 'hours' => 'Режим работы' ] as $k => $label ) {
		foreach ( $langs as $slug => $l ) {
			$contacts[ $k . '_' . $slug ] = [ $label . ' — ' . $l['name'], 'text' ];
		}
	}

	$images = [];
	foreach (
		[
			'img_hero_1'   => 'Первый экран — слайд 1',
			'img_hero_2'   => 'Первый экран — слайд 2',
			'img_hero_3'   => 'Первый экран — слайд 3',
			'img_award'    => 'Награда Best for Life Design (значок или фото)',
			'img_meet'     => 'Блок «Встречайте EVERSENSE»',
			'img_solution' => 'Блок «Решение от EVERSENSE»',
			'img_feat_1'   => 'Преимущество: гарантия',
			'img_feat_2'   => 'Преимущество: вода',
			'img_feat_3'   => 'Преимущество: износ',
			'img_feat_4'   => 'Преимущество: удар',
			'img_eco'      => 'Блок «Экологичное производство»',
			'img_textures' => 'Блок «Текстуры для проектов»',
			'img_trust'    => 'Блок «Нам важно ваше доверие»',
		] as $k => $label
	) {
		$images[ $k ] = [ $label, 'image' ];
	}

	return [
		'Контакты дистрибьютора' => $contacts,
		'Соцсети'                => [
			'telegram'  => [ 'Telegram', 'url' ],
			'instagram' => [ 'Instagram', 'url' ],
			'vk'        => [ 'ВКонтакте', 'url' ],
			'facebook'  => [ 'Facebook', 'url' ],
		],
		'Документы и файлы'      => [
			'textures_url'    => [ 'Архив текстур для дизайнеров', 'url' ],
			'iso9001_url'     => [ 'Сертификат ISO 9001:2015', 'url' ],
			'iso14001_url'    => [ 'Сертификат ISO 14001:2015', 'url' ],
			'booklet_1_url'   => [ 'Буклет 1', 'url' ],
			'booklet_2_url'   => [ 'Буклет 2', 'url' ],
			'instruction_url' => [ 'Инструкция по укладке', 'url' ],
		],
		'Видео (mp4)'            => [
			'video_1' => [ 'Видео в блоке «Баланс красоты и практичности»', 'url' ],
			'video_2' => [ 'Видео в блоке «Вы видите, чувствуете, слышите дерево»', 'url' ],
		],
		'Фото на главной'        => $images,
		'Сервисы'                => [
			'show_award' => [ 'Показывать блок награды на главной', 'checkbox' ],
			'yandex_key' => [ 'Ключ API Яндекс Карт (для страницы «Где купить»)', 'text' ],
			'metrika_id' => [ 'Номер счётчика Яндекс Метрики', 'text' ],
		],
	];
}

add_action(
	'admin_menu',
	static function () {
		add_theme_page( 'Настройки EVERSENSE', 'Настройки EVERSENSE', 'manage_options', 'ev-settings', 'ev_render_settings' );
	}
);

add_action(
	'admin_init',
	static function () {
		register_setting(
			'ev_settings',
			'ev_settings',
			[
				'type'              => 'array',
				'sanitize_callback' => 'ev_sanitize_settings',
			]
		);
	}
);

function ev_sanitize_settings( $in ) {
	$out = [];
	foreach ( ev_option_schema() as $fields ) {
		foreach ( $fields as $key => $f ) {
			if ( 'checkbox' === $f[1] ) {
				$out[ $key ] = empty( $in[ $key ] ) ? '0' : '1';
				continue;
			}
			$out[ $key ] = isset( $in[ $key ] ) ? ev_clean_field( $f[1], $in[ $key ] ) : '';
		}
	}
	return $out;
}

function ev_render_settings() {
	if ( ! current_user_can( 'manage_options' ) ) {
		return;
	}
	?>
	<div class="wrap">
		<h1>Настройки EVERSENSE — <?php echo esc_html( ev_country( 'name' ) ); ?></h1>
		<p>Тексты главной страницы лежат в файлах темы <code>lang/ru.php</code> и <code>lang/be.php</code>. Здесь — то, что отличается у дистрибьютора: контакты, ссылки, фото.</p>
		<form method="post" action="options.php">
			<?php settings_fields( 'ev_settings' ); ?>
			<?php foreach ( ev_option_schema() as $group => $fields ) : ?>
				<h2 class="title"><?php echo esc_html( $group ); ?></h2>
				<table class="form-table" role="presentation">
					<?php foreach ( $fields as $key => $f ) : ?>
						<tr>
							<th><label for="ev_settings_<?php echo esc_attr( $key ); ?>"><?php echo esc_html( $f[0] ); ?></label></th>
							<td>
								<?php
								$name  = 'ev_settings[' . $key . ']';
								$value = ev_opt( $key );
								if ( 'checkbox' === $f[1] ) {
									printf( '<input type="hidden" name="%1$s" value="0"><label><input type="checkbox" name="%1$s" value="1" %2$s> Да</label>', esc_attr( $name ), checked( '1', $value, false ) );
								} else {
									ev_render_field( $name, $f[1], $value );
								}
								?>
							</td>
						</tr>
					<?php endforeach; ?>
				</table>
			<?php endforeach; ?>
			<?php submit_button(); ?>
		</form>
	</div>
	<?php
}

/** Ссылка на настройки в списке тем. */
add_action(
	'admin_bar_menu',
	static function ( $bar ) {
		if ( current_user_can( 'manage_options' ) && ! is_admin() ) {
			$bar->add_node( [ 'id' => 'ev-settings', 'title' => 'Настройки EVERSENSE', 'href' => admin_url( 'themes.php?page=ev-settings' ) ] );
		}
	},
	80
);
