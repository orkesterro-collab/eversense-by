<?php
defined( 'ABSPATH' ) || exit;
if ( ! ev_opt( 'textures_url' ) ) {
	return;
}
?>
<section class="ev-textures ev-section--tight">
	<div class="ev-container">
		<div class="ev-textures__card ev-dark" data-reveal>
			<div class="ev-textures__media"><?php echo ev_media( 'img_textures', 'dark', '', 'ev-wide' ); // phpcs:ignore ?></div>
			<div class="ev-textures__body">
				<h2 class="ev-h2"><?php ev_e( 'textures_title' ); ?></h2>
				<p><?php ev_e( 'textures_text' ); ?></p>
				<a class="ev-btn ev-btn--light" href="<?php echo esc_url( ev_opt( 'textures_url' ) ); ?>" target="_blank" rel="noopener">
					<?php echo ev_icon( 'download' ); // phpcs:ignore ?> <?php ev_e( 'textures_button' ); ?>
				</a>
			</div>
		</div>
	</div>
</section>
