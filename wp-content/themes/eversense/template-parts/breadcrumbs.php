<?php
/** Хлебные крошки. $args: items — [[label, url|null], …] после «Главная». */
defined( 'ABSPATH' ) || exit;
$items = array_merge( [ [ ev_t( 'home' ), ev_home_url() ] ], $args['items'] ?? [] );
?>
<nav class="ev-crumbs" aria-label="breadcrumbs">
	<ol>
		<?php foreach ( $items as $i => $it ) : ?>
			<li>
				<?php if ( ! empty( $it[1] ) && $i < count( $items ) - 1 ) : ?>
					<a href="<?php echo esc_url( $it[1] ); ?>"><?php echo esc_html( $it[0] ); ?></a>
				<?php else : ?>
					<span aria-current="page"><?php echo esc_html( $it[0] ); ?></span>
				<?php endif; ?>
			</li>
		<?php endforeach; ?>
	</ol>
</nav>
