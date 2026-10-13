<?php defined( 'ABSPATH' ) || exit; ?>
<section class="ev-senses ev-dark">
	<div class="ev-senses__media"><?php echo ev_video( 'video_2', 'dark' ); // phpcs:ignore ?></div>
	<div class="ev-frame" aria-hidden="true"></div>
	<div class="ev-container ev-senses__inner">
		<ul class="ev-senses__list">
			<?php foreach ( [ 'see' => 'eye', 'feel' => 'hand', 'hear' => 'ear' ] as $k => $icon ) : ?>
				<li class="ev-sense" data-reveal>
					<?php echo ev_icon( $icon, 'ev-sense__icon' ); // phpcs:ignore ?>
					<h2 class="ev-sense__title"><?php ev_e( 'sense_' . $k . '_title' ); ?></h2>
					<p class="ev-sense__text"><?php ev_e( 'sense_' . $k . '_text' ); ?></p>
				</li>
			<?php endforeach; ?>
		</ul>
	</div>
</section>
