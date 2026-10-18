<?php defined('ABSPATH') || exit; get_header(); ?>
<section class="ev-section--tight ev-beige"><div class="ev-container">
<p class="ev-eyebrow">EVERSENSE / Беларусь</p>
<h1 class="ev-display"><?php echo esc_html(ev_t('menu_projects')); ?></h1>
<p class="ev-lead">Реальные интерьеры с напольными покрытиями EVERSENSE. Откройте проект, чтобы увидеть использованные декоры.</p>
<?php if(have_posts()): ?><div class="ev-project-grid">
<?php while(have_posts()):the_post(); ?>
<a class="ev-project-tile" href="<?php the_permalink(); ?>">
<?php if(has_post_thumbnail()):the_post_thumbnail('ev-card',['loading'=>'lazy']);else: ?><span class="ev-project-empty">EVERSENSE</span><?php endif; ?>
<strong><?php the_title(); ?></strong>
<span><?php echo esc_html(get_the_excerpt()); ?></span>
</a>
<?php endwhile; ?></div><?php the_posts_pagination(); ?>
<?php else: ?><p>Галерея пополняется. Пока опубликованных проектов нет.</p><?php endif; ?>
</div></section><?php get_footer(); ?>