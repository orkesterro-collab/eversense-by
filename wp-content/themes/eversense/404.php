<?php
defined( 'ABSPATH' ) || exit;
get_header();
?>
<section class="ev-404 ev-section">
	<div class="ev-pattern ev-pattern--soft" aria-hidden="true"></div>
	<div class="ev-container ev-container--narrow">
		<p class="ev-404__code">404</p>
		<h1 class="ev-h1"><?php ev_e( 'not_found_title' ); ?></h1>
		<p class="ev-lead"><?php ev_e( 'not_found_text' ); ?></p>
		<div class="ev-btn-row">
			<a class="ev-btn" href="<?php echo esc_url( ev_catalog_url() ); ?>"><?php ev_e( 'view_catalog' ); ?></a>
			<a class="ev-btn ev-btn--ghost" href="<?php echo esc_url( ev_home_url() ); ?>"><?php ev_e( 'home' ); ?></a>
		</div>
	</div>
</section>
<?php
get_footer();
