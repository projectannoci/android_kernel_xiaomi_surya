#define FLOOR SINGULARITY_GPU_SAMPLE_US
#define MIN_BUSY		1000
#define CEILING			50000
static inline int devfreq_get_freq_level(struct devfreq *devfreq,
	unsigned long freq)
{
	int lev;

	for (lev = 0; lev < devfreq->profile->max_state; lev++)
		if (freq == devfreq->profile->freq_table[lev])
			return lev;

	return -EINVAL;
}

static int tz_get_target_freq(struct devfreq *devfreq, unsigned long *freq)
{
	int result = 0;
	struct devfreq_msm_adreno_tz_data *priv = devfreq->data;
	struct devfreq_dev_status stats;
	int val = 0, level = 0;
	unsigned int scm_data[4];
	int context_count = 0;

	/* keeps stats.private_data == NULL   */
	result = devfreq->profile->get_dev_status(devfreq->dev.parent, &stats);
	if (result) {
		pr_err(TAG "get_status failed %d\n", result);
		return result;
	}

	*freq = stats.current_frequency;
	priv->bin.total_time += stats.total_time;
	priv->bin.busy_time += stats.busy_time;

	if (stats.private_data)
		context_count =  *((int *)stats.private_data);

	/* Update the GPU load statistics */
	compute_work_load(&stats, priv, devfreq);
	/*
	 * Do not waste CPU cycles running this algorithm if
	 * the GPU just started, or if less than FLOOR time
	 * has passed since the last run or the gpu hasn't been
	 * busier than MIN_BUSY.
	 */
	if ((stats.total_time == 0) ||
		(priv->bin.total_time < FLOOR) ||
		(unsigned int) priv->bin.busy_time < MIN_BUSY) {
		return 0;
	}

	level = devfreq_get_freq_level(devfreq, stats.current_frequency);
	if (level < 0) {
		pr_err(TAG "bad freq %ld\n", stats.current_frequency);
		return level;
	}

	/*
	 * If there is an extended block of busy processing,
	 * increase frequency.  Otherwise run the normal algorithm.
	 */
	if (!priv->disable_busy_time_burst &&
			priv->bin.busy_time > CEILING) {
		val = -1 * level;
	} else {
		unsigned int refresh_rate = dsi_panel_get_refresh_rate();

		scm_data[0] = level;
		scm_data[1] = priv->bin.total_time;
		if (refresh_rate > 60)
			scm_data[2] = priv->bin.busy_time * refresh_rate / 60;
		else
			scm_data[2] = priv->bin.busy_time;
		scm_data[3] = context_count;
		result = __secure_tz_update_entry3(scm_data, sizeof(scm_data),
					&val, sizeof(val), priv);
		if (result) {
			priv->bin.total_time = 0;
			priv->bin.busy_time = 0;
			return result;
		}
	}
	/*
	 * If the decision is to move to a different level, make sure the GPU
	 * frequency changes.
	 */
	if (!priv->disable_busy_time_burst) {
		level = singularity_gpu_level(level,
			devfreq->profile->max_state - 1, val,
			priv->bin.busy_time, priv->bin.total_time);
	} else if (val) {
		level += val;
		level = max(level, 0);
		level = min_t(int, level, devfreq->profile->max_state - 1);
	}

	priv->bin.total_time = 0;
	priv->bin.busy_time = 0;
	*freq = devfreq->profile->freq_table[level];
	return 0;
}

