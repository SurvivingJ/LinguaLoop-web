do $$
declare
  u uuid := '110fb390-0c84-4852-bb52-f7cca62a91cc'; l smallint := 3;
  r jsonb := '{}'; a numeric[]; t timestamptz; n int := 30; x text;
  fns text[] := array['resolve_plan_timezone','plan_local_date','review_governor_state','ladder_new_word_state',
    'record_session_progress','credit_study_time','apply_attempt_timing_and_progress','get_recommended_tests',
    'compute_weekly_plan_load_signals','build_daily_session'];
  f text;
begin
  foreach f in array fns loop
    a := '{}';
    for i in 1..(case when f='build_daily_session' then 15 else n end) loop
      t := clock_timestamp();
      case f
        when 'resolve_plan_timezone' then perform public.resolve_plan_timezone('Asia/Tokyo');
        when 'plan_local_date' then perform public.plan_local_date(u, l);
        when 'review_governor_state' then perform public.review_governor_state(u, l, current_date);
        when 'ladder_new_word_state' then perform public.ladder_new_word_state(u, l, date_trunc('day', now()));
        when 'record_session_progress' then perform public.record_session_progress(u, l, gen_random_uuid(), 'test', 'reading', 1, 1, 0);
        when 'credit_study_time' then perform public.credit_study_time(u, l, 'practice', 60, 'bench', gen_random_uuid()::text);
        when 'apply_attempt_timing_and_progress' then perform public.apply_attempt_timing_and_progress('d386b3a3-d811-4901-a2b7-1a45660f26df'::uuid, null, null);
        when 'get_recommended_tests' then perform * from public.get_recommended_tests(u, l, 7::smallint);
        when 'compute_weekly_plan_load_signals' then perform public.compute_weekly_plan_load_signals(u, l, public.week_start_for(current_date));
        when 'build_daily_session' then perform public.build_daily_session(u, l, current_date);
      end case;
      a := a || round(extract(epoch from clock_timestamp() - t)::numeric * 1000, 2);
    end loop;
    r := r || jsonb_build_object(f, to_jsonb(a));
  end loop;
  raise exception 'BENCH%', r::text;   -- rolls back every write above
end $$;
