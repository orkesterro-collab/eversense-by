<?php defined( 'ABSPATH' ) || exit; ?>
<section class="ev-trust ev-section">
	<div class="ev-container ev-split ev-split--center">
		<div class="ev-split__media ev-framed" data-reveal><?php echo ev_media( 'img_trust', 'light', '', 'ev-card' ); // phpcs:ignore ?></div>
		<div class="ev-split__text" data-reveal>
			<h2 class="ev-display"><?php ev_e( 'trust_title' ); ?></h2>
			<p class="ev-lead"><?php ev_e( 'trust_lead' ); ?></p>
			<p><?php ev_e( 'trust_text' ); ?></p>
			<a class="ev-btn" href="<?php echo esc_url( ev_catalog_url() ); ?>"><?php ev_e( 'view_catalog' ); ?></a>
		</div>
	</div>
</section>
