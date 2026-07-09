import os, os.path
big = []
for root, dirs, files in os.walk(r'C:\Users\gbx12'):
    try:
        sz = sum(os.path.getsize(os.path.join(root, f)) for f in files if os.path.isfile(os.path.join(root, f)))
        if sz > 100*1024*1024:
            big.append((sz, root))
    except:
        pass
big.sort(reverse=True)
for sz, p in big[:15]:
    print(f'{sz//1024//1024}MB  {p}')
