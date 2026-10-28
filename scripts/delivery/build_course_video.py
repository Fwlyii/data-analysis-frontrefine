"""Build a 340-second 1080P research presentation from the current slide PDF.

This is a graph/slide presentation, not a claimed browser recording. Uses local
macOS speech synthesis, Poppler, Pillow and FFmpeg. No model/network APIs.
"""
from pathlib import Path
import argparse,json,math,re,shutil,subprocess,sys
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'project.json').is_file())
def run(args):return subprocess.run([str(x) for x in args],check=True,capture_output=True)
def duration(ffmpeg,path):
 r=subprocess.run([ffmpeg,'-hide_banner','-i',str(path)],capture_output=True,text=True);m=re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)',r.stderr)
 if not m:raise ValueError('Cannot read audio duration')
 return int(m[1])*3600+int(m[2])*60+float(m[3])
def stamp(t):
 ms=round(t*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000);return f'{h:02}:{m:02}:{s:02},{ms:03}'
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pdftoppm',default=shutil.which('pdftoppm'));p.add_argument('--ffmpeg');p.add_argument('--voice',default='Tingting');p.add_argument('--font',default='/System/Library/Fonts/Supplemental/Arial Unicode.ttf');a=p.parse_args()
 if not a.pdftoppm:raise SystemExit('Install Poppler or set --pdftoppm.')
 if not a.ffmpeg:
  import imageio_ffmpeg;a.ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
 if not Path('/usr/bin/say').exists():raise SystemExit('Local speech generation requires macOS say; use supplied finished MP4 elsewhere.')
 from PIL import Image,ImageDraw,ImageFont
 out=ROOT/'presentation';work=ROOT/'build/current_video';work.mkdir(parents=True,exist_ok=True)
 slides=json.loads((out/'current_slide_content.json').read_text())
 run([a.pdftoppm,'-scale-to-x','1920','-scale-to-y','1080','-png',out/'defense_slides.pdf',work/'slide'])
 times=[]
 for i,s in enumerate(slides,1):
  txt=work/f'narration-{i:02}.txt';txt.write_text(s['speech']);audio=work/f'audio-{i:02}.aiff'
  run(['/usr/bin/say','-v',a.voice,'-r','220','-f',txt,'-o',audio]);times.append(duration(a.ffmpeg,audio));print(f'speech {i}/12',flush=True)
 total_frames=8500;raw=[t/sum(times)*total_frames for t in times];frames=[math.floor(t) for t in raw]
 for i in sorted(range(len(frames)),key=lambda i:raw[i]-frames[i],reverse=True)[:total_frames-sum(frames)]:frames[i]+=1
 font=ImageFont.truetype(a.font,29);captions=[];start=0.;segments=[]
 for i,(s,n,spoken) in enumerate(zip(slides,frames,times),1):
  seconds=n/25;image=Image.open(work/f'slide-{i:02}.png').convert('RGB');draw=ImageDraw.Draw(image)
  draw.rectangle((0,980,1920,1080),fill=(239,244,247));caption=s['title']
  bbox=draw.textbbox((0,0),caption,font=font);draw.text(((1920-(bbox[2]-bbox[0]))/2,1031),caption,font=font,fill='#243c52')
  image_path=work/f'frame-{i:02}.png';image.save(image_path)
  rate=spoken/seconds;factors=[]
  while rate>2:factors.append(2);rate/=2
  while rate<.5:factors.append(.5);rate/=.5
  factors.append(rate);af=','.join('atempo='+str(x) for x in factors)+',apad'
  movie=work/f'segment-{i:02}.mp4'
  run([a.ffmpeg,'-y','-loglevel','error','-loop','1','-framerate','25','-i',image_path,'-i',work/f'audio-{i:02}.aiff','-af',af,'-t',str(seconds),'-c:v','libx264','-preset','veryfast','-crf','21','-tune','stillimage','-pix_fmt','yuv420p','-r','25','-c:a','aac','-b:a','160k','-ar','48000',movie]);segments.append(movie)
  captions.append(f'{i}\n{stamp(start)} --> {stamp(start+seconds)}\n{s["title"]}\n');start+=seconds;print(f'video {i}/12',flush=True)
 concat=work/'concat.txt';concat.write_text('\n'.join("file '"+p.name+"'" for p in segments)+'\n')
 dest=out/'research_demo_340s.mp4';run([a.ffmpeg,'-y','-loglevel','error','-f','concat','-safe','0','-i',concat,'-c','copy','-movflags','+faststart',dest])
 (out/'research_demo.srt').write_text('\n'.join(captions)+'\n')
 metadata={'type':'research-slide-presentation','not_browser_recording':True,'target_duration_seconds':340,'duration_seconds':duration(a.ffmpeg,dest),'subtitles':'slide titles','video_frames':8500,'width':1920,'height':1080,'fps':25,'narration':'local macOS speech synthesis','model_api_calls':0,'slide_frames':frames,'source':'presentation/defense_slides.pdf'}
 (out/'current_video.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n');print('Created current 340s research presentation.',flush=True)
if __name__=='__main__':main()
