import type { IndustryId } from './home-content'

/**
 * Professional portrait photos from Unsplash (Unsplash License).
 * Local PNG cutouts (transparent background) in /public/industries/.
 *
 * Sources:
 * - fashion: https://unsplash.com/photos/98_Q-M8WttQ (Vitaly Gariev)
 * - education: https://unsplash.com/photos/TOuMSV0Nqjk (Vitaly Gariev)
 * - health: https://unsplash.com/photos/ODM_VsTM2QQ (Bermix Studio)
 * - restaurants: https://unsplash.com/photos/b9BVeBMTqqA (Zayed Ahmed Zadu)
 * - spa: https://unsplash.com/photos/A5xiXjyxmAU (Land O'Lakes, Inc.)
 */
export const INDUSTRY_PERSON_IMAGES: Record<IndustryId, { src: string; alt: string }> = {
  fashion: {
    src: '/industries/fashion.png',
    alt: 'Fashion model posing in studio',
  },
  education: {
    src: '/industries/education.png',
    alt: 'Teacher with notebook at desk',
  },
  health: {
    src: '/industries/health.png',
    alt: 'Healthcare professional in white coat',
  },
  restaurants: {
    src: '/industries/restaurants.png',
    alt: 'Professional chef in uniform',
  },
  spa: {
    src: '/industries/spa.png',
    alt: 'Beauty salon stylist',
  },
}
