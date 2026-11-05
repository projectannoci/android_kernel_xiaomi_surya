/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_SINGULARITY_DVFS_H
#define _LINUX_SINGULARITY_DVFS_H

#define SINGULARITY_GPU_SAMPLE_US 2000U

/* Capacity-relative demand headroom; zero demand stays zero. */
static inline unsigned long singularity_cpu_util(unsigned long util,
		unsigned long capacity, int big)
{
	unsigned long margin;

	if (!capacity)
		return 0;
	if (util > capacity)
		util = capacity;
	if (util < (big ? capacity / 2 : capacity - capacity / 4))
		return util;
	margin = big ? capacity / 8 : capacity / 16;
	return util > capacity - margin ? capacity : util + margin;
}

/* Avoid overflowing a 64-bit sample when comparing load percentages. */
static inline unsigned long long singularity_load_threshold(
		unsigned long long total, unsigned int percent)
{
	return (total / 100) * percent +
		((total % 100) * percent + 99) / 100;
}

/* Lower index means higher frequency in the KGSL frequency table. */
static inline unsigned int singularity_gpu_level(unsigned int level,
		unsigned int last, int tz_delta, unsigned long long busy,
		unsigned long long total)
{
	long long requested;
	unsigned int target, burst;

	if (level > last)
		level = last;
	requested = (long long)level + tz_delta;
	target = requested < 0 ? 0 : requested > last ? last : requested;
	if (total < SINGULARITY_GPU_SAMPLE_US || busy > total)
		return target;
	if (busy >= singularity_load_threshold(total, 90)) {
		burst = level > 1 ? level - 2 : 0;
		if (target > burst)
			target = burst;
	} else if (busy >= singularity_load_threshold(total, 75)) {
		burst = level ? level - 1 : 0;
		if (target > burst)
			target = burst;
	} else if (busy >= singularity_load_threshold(total, 60) &&
			target > level) {
		target = level;
	}
	return target;
}
#endif
