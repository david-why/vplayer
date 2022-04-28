#ifndef __INT24_TYPE__
#define __INT24_TYPE__ int
#define __INT24_MAX__ 0x7fffff
#define __INT24_MIN__ (~__INT24_MAX__)
typedef __INT24_TYPE__ int24_t;
#define __UINT24_TYPE__ unsigned int
#define __UINT24_MAX__ 0xffffff
typedef __UINT24_TYPE__ uint24_t;
#endif

#include <tice.h>
#include <stdio.h>
#include <graphx.h>
#include <time.h>
#include "fatutils.h"

#define vram ((uint8_t *)0xD40000)

char buf[256];
void *glob_data;

struct vfile_head
{
    uint8_t framerate;
    uint8_t version;
    uint8_t head[511];
};

typedef bool (*init_t)(vfile_head *);
typedef bool (*nxtframe_t)(fat_file_t *, vfile_head *);
typedef void (*deinit_t)();

bool return_true(vfile_head *) { return true; }
bool ver_sprite_init(vfile_head *head)
{
    gfx_Begin();
    gfx_SetDrawBuffer();
    glob_data = malloc(head->head[2] * FAT_BLOCK_SIZE + 2);
    *(uint8_t *)glob_data = head->head[0];
    ((uint8_t *)glob_data)[1] = head->head[1];
    return true;
}

bool ver_fullscreen(fat_file_t *file, vfile_head *)
{
    unsigned int read = 0;
    for (uint8_t i = 0; i < 10; i++)
        read += fat_Read(file, 30, vram + i * 30 * FAT_BLOCK_SIZE);
    if (read != 300)
        return false;
    return true;
}
bool ver_sprite(fat_file_t *file, vfile_head *head)
{
    // gfx_TempSprite(sprite, head->head[0], head->head[1]);
    unsigned int read = 0;
    for (uint8_t i = 0; i < head->head[2]; i++)
        read += fat_Read(file, 1, ((gfx_sprite_t *)glob_data)->data + FAT_BLOCK_SIZE * i);
    if (read != head->head[2])
        return false;
    uint8_t wscale = 320 / head->head[0];
    uint8_t hscale = 240 / head->head[1];
    // gfx_Sprite((gfx_sprite_t *)glob_data, 0, 0);
    // unsigned int read = 0;
    // for (uint8_t i = 0; i < head->head[2]; i++)
    //     read += fat_Read(file, 1, ((uint8_t *)glob_data) + FAT_BLOCK_SIZE * i);
    // if (read != head->head[2])
    //     return false;
    // for (unsigned int y = 0; y < head->head[1]; y++)
    //     memcpy(gfx_vbuffer[y], ((uint8_t *)glob_data) + y * head->head[0], head->head[0]);
    gfx_ScaledSprite_NoClip((gfx_sprite_t *)glob_data, 0, 0, wscale, hscale);
    gfx_SwapDraw();
    return true;
}

void do_nothing() {}
void ver_sprite_deinit()
{
    gfx_End();
    free(glob_data);
}

struct version_t
{
    const init_t init;
    const nxtframe_t nxtframe;
    const deinit_t deinit;
} const vers[] = {{return_true, ver_fullscreen, do_nothing}, {ver_sprite_init, ver_sprite, ver_sprite_deinit}};

int main()
{
    clock();
    CLOCKS_PER_SEC;
    puts("Waiting for USB...");
    uint8_t err = fatutil_Init(10);
    if (err)
    {
        puts("FAT init error");
        os_GetKey();
        return 0;
    }

    auto lst = fatutil_ListDir("/VPLAYER", FAT_LIST_FILEONLY);
    if (lst.empty())
    {
        puts("No videos found");
        fatutil_Deinit();
        os_GetKey();
        return 0;
    }

    uint8_t fsel = 0;
    os_ClrHome();
    while (true)
    {
        sprintf(buf, "Showing %u of %u  ", fsel + 1, lst.size());
        os_HomeUp();
        puts(buf);
        puts("");
        puts("Filename:");
        sprintf(buf, "%s       ", lst[fsel].entry.filename);
        puts(buf);

        sk_key_t key;
        while (!(key = os_GetCSC()))
            ;
        if (key == sk_Left)
        {
            if (fsel == 0)
                fsel = lst.size();
            fsel--;
        }
        else if (key == sk_Right)
        {
            fsel++;
            if (fsel == lst.size())
                fsel = 0;
        }
        else if (key == sk_Enter)
            break;
    }

    sprintf(buf, "/VPLAYER/%s", lst[fsel].entry.filename);
    fat_file_t file;
    fat_Open(&file, fatutil_GetFAT(), buf);
    vfile_head head;
    fat_Read(&file, 1, &head);
    timer_Enable(2, TIMER_32K, TIMER_0INT, TIMER_UP);

    if (vers[head.version].init(&head))
    {
        unsigned long clk = CLOCKS_PER_SEC / head.framerate;
        unsigned long c = clock();
        while (true)
        {
            if (!vers[head.version].nxtframe(&file, &head))
                break;
            sk_key_t key = os_GetCSC();
            if (key == sk_Clear)
                break;
            while (clock() - c < clk)
                ;
            c = clock();
        }
    }
    vers[head.version].deinit();

    os_ClrHome();
    fat_Close(&file);
    fatutil_Deinit();

    return 0;
}
