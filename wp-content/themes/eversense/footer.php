<?php defined( 'ABSPATH' ) || exit; ?>
</main>

<footer class="ev-footer ev-dark">
	<div class="ev-pattern ev-pattern--footer" aria-hidden="true"></div>
	<div class="ev-container">
		<p class="ev-footer__tagline">
			<span><?php ev_e( 'footer_tagline_1' ); ?></span>
			<?php ev_e( 'footer_tagline_2' ); ?>
		</p>

		<div class="ev-footer__grid">
			<div class="ev-footer__brand">
				<a class="ev-logo ev-logo--light" href="<?php echo esc_url( ev_home_url() ); ?>"><?php echo ev_logo( 'full' ); // phpcs:ignore WordPress.Security.EscapeOutput ?></a>
				<p class="ev-footer__distributor"><?php ev_e( 'footer_distributor' ); ?><br><?php echo esc_html( ev_opt_l( 'company' ) ); ?></p>
			</div>

			<nav class="ev-footer__col" aria-label="<?php echo esc_attr( ev_t( 'menu_catalog' ) ); ?>">
				<?php foreach ( ev_nav_items() as $item ) : ?>
					<a href="<?php echo esc_url( $item['url'] ); ?>"><?php echo esc_html( $item['label'] ); ?></a>
				<?php endforeach; ?>
			</nav>

			<div class="ev-footer__col">
				<p class="ev-footer__label"><?php ev_e( 'footer_downloads' ); ?></p>
				<?php
				$docs = [
					'booklet_1_url'   => ev_t( 'footer_booklet' ),
					'booklet_2_url'   => ev_t( 'footer_booklet' ) . ' 2',
					'instruction_url' => ev_t( 'footer_instruction' ),
					'iso9001_url'     => ev_t( 'footer_iso9001' ),
					'iso14001_url'    => ev_t( 'footer_iso14001' ),
				];
				foreach ( $docs as $key => $label ) :
					if ( ! ev_opt( $key ) ) {
						continue;
					}
					?>
					<a href="<?php echo esc_url( ev_opt( $key ) ); ?>" target="_blank" rel="noopener"><?php echo esc_html( $label ); ?></a>
				<?php endforeach; ?>
			</div>

			<div class="ev-footer__col">
				<?php if ( ev_opt( 'phone' ) ) : ?>
					<a class="ev-footer__phone" href="<?php echo esc_attr( ev_tel( ev_opt( 'phone' ) ) ); ?>"><?php echo esc_html( ev_opt( 'phone' ) ); ?></a>
				<?php endif; ?>
				<?php if ( ev_opt( 'email' ) ) : ?>
					<a href="mailto:<?php echo esc_attr( ev_opt( 'email' ) ); ?>"><?php echo esc_html( ev_opt( 'email' ) ); ?></a>
				<?php endif; ?>
				<?php if ( ev_opt_l( 'office' ) ) : ?>
					<span><?php echo esc_html( ev_opt_l( 'office' ) ); ?></span>
				<?php endif; ?>
				<?php get_template_part( 'template-parts/social' ); ?>
			</div>
		</div>

		<div class="ev-footer__bottom">
			<span>© <?php echo esc_html( gmdate( 'Y' ) ); ?> EVERSENSE</span>
			<?php if ( ev_opt_l( 'requisites' ) ) : ?>
				<span><?php echo esc_html( ev_opt_l( 'requisites' ) ); ?></span>
			<?php endif; ?>
			<a href="<?php echo esc_url( ev_page_url( 'privacy' ) ); ?>"><?php ev_e( 'footer_privacy' ); ?></a>
		</div>
	</div>
</footer>

<div class="ev-cookie" hidden data-cookie>
	<p>
		<?php
		$text = esc_html( ev_t( 'cookie_text' ) );
		$link = '<a href="' . esc_url( ev_page_url( 'privacy' ) ) . '">' . esc_html( ev_t( 'cookie_link' ) ) . '</a>';
		echo str_replace( esc_html( ev_t( 'cookie_link' ) ), $link, $text ); // phpcs:ignore WordPress.Security.EscapeOutput
		?>
	</p>
	<button class="ev-btn ev-btn--small" type="button" data-cookie-ok><?php ev_e( 'cookie_ok' ); ?></button>
</div>

<?php wp_footer(); ?>
</body>
</html>
