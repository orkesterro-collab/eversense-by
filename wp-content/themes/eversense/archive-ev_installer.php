<?php defined('ABSPATH') || exit; get_header(); ?>
<section class="ev-section--tight ev-beige"><div class="ev-container">
<p class="ev-eyebrow">EVERSENSE / Беларусь</p><h1 class="ev-display"><?php echo esc_html(ev_t('menu_installers')); ?></h1>
<p class="ev-lead">Специалисты по укладке напольных покрытий. Отметка «Проверен» означает проверку дистрибьютором, но не заменяет договор и гарантию на монтаж.</p>
<?php if(have_posts()): ?><div class="ev-installer-grid"><?php while(have_posts()):the_post();$id=get_the_ID();$phone=get_post_meta($id,'ev_phone',true);$city=get_post_meta($id,'ev_city',true);$site=get_post_meta($id,'ev_site',true); ?>
<article class="ev-installer-card">
<?php if(has_post_thumbnail()): ?><div class="ev-installer-avatar"><?php the_post_thumbnail('thumbnail'); ?></div><?php endif; ?>
<h2 class="ev-h4"><?php the_title(); ?></h2><p><?php echo esc_html($city); ?></p>
<?php if('1'===get_post_meta($id,'ev_verified',true)): ?><span class="ev-verified">✓ Проверен дистрибьютором</span><?php endif; ?>
<div class="ev-prose"><?php the_excerpt(); ?></div>
<?php if($phone): ?><a href="<?php echo esc_attr(ev_tel($phone)); ?>"><?php echo esc_html($phone); ?></a><?php endif; ?>
<?php if($site): ?><a href="<?php echo esc_url($site); ?>" rel="nofollow noopener" target="_blank">Сайт / портфолио ↗</a><?php endif; ?>
</article><?php endwhile; ?></div><?php the_posts_pagination(); ?>
<?php else: ?><p>Список проверенных специалистов пока формируется. Мы не публикуем чужие контакты без согласия.</p><?php endif; ?>
</div></section><?php get_footer(); ?>