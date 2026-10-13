<?php
defined( 'ABSPATH' ) || exit;
if ( '1' !== (string) ev_opt( 'show_award' ) ) {
	return;
}
?>
<section class="ev-award ev-section--tight">
	<div class="ev-container ev-award__inner">
		<div class="ev-award__badge">
			<?php if ( ev_opt( 'img_award' ) ) : ?>
				<?php echo ev_media( 'img_award', 'light', '', 'medium', 'Best for Life Design' ); // phpcs:ignore ?>
			<?php else : ?>
				<span class="ev-award__seal">
					<span class="ev-award__seal-top"><?php ev_e( 'award_badge' ); ?></span>
					<span class="ev-award__seal-main">Best for Life<br>Design</span>
				</span>
			<?php endif; ?>
		</div>
		<div class="ev-award__body">
			<h2 class="ev-h3"><?php ev_e( 'award_title' ); ?></h2>
			<p><?php ev_e( 'award_text' ); ?></p>
			<a class="ev-link-arrow" href="<?php echo esc_url( ev_catalog_url() ); ?>"><?php ev_e( 'view_collection' ); ?> <?php echo ev_icon( 'arrow-r' ); // phpcs:ignore ?></a>
		</div>
	</div>
</section>
