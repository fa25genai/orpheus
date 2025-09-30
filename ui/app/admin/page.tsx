"use client";
import {Badge} from "@/components/ui/badge";
import {Button} from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {Tabs, TabsContent, TabsList, TabsTrigger} from "@/components/ui/tabs";
import {
  ArrowLeft,
  CircleUser,
  FileText,
  File,
  Video,
  Volume2,
} from "lucide-react";
import Link from "next/link";
import {useState} from "react";
import {FileUpload} from "@/components/file-upload";
import {UploadedFile} from "@/types/uploading";
import {docintApi} from "../api-clients";
import {makeUploadHandler, makeRemoveHandler} from "@/helper/upload-helper";
import {courseId} from "@/data/course";
import {AvatarUpload} from "@/components/avatar-upload";
import {AudioUpload} from "@/components/audio-upload";

export default function Admin() {
  const [activeTab, setActiveTab] = useState("material");

  // State for each file type
  const [slides, setSlides] = useState<UploadedFile[]>([]);
  const [videos, setVideos] = useState<UploadedFile[]>([]);
  // --------------------
  // Handlers for Slides
  // --------------------
  const handleSlidesUpload = makeUploadHandler(setSlides, async (file) => {
    const response = await docintApi.uploadsDocument({
      courseId,
      body: file,
    });
    return {documentId: response.documentId};
  });

  const handleSlidesRemove = makeRemoveHandler(setSlides, async (file) => {
    if (!file.documentId) throw new Error("No documentId");
    await docintApi.deletesDocument({documentId: file.documentId});
  });

  // --------------------
  // Handlers for Videos
  // --------------------
  const handleVideosUpload = makeUploadHandler(setVideos, async (file) => {
    const response = await docintApi.uploadsVideo({
      courseId,
      body: file,
    });
    return {documentId: response.videoId};
  });

  const handleVideosRemove = makeRemoveHandler(setVideos, async (file) => {
    console.log(file);
    await new Promise((r) => setTimeout(r, 500));
  });

  return (
    <main>
      <header className="p-4 border-b border-border mb-6">
        <div className="max-w-6xl mx-auto flex items-center justify-evenly gap-6">
          <Link href="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Student View
            </Button>
          </Link>

          <div>
            <h1 className="text-2xl font-bold">Orpheus Admin Dashboard</h1>
            <p className="text-muted-foreground">
              Manage your interactive lecture content
            </p>
          </div>

          <Badge
            variant="secondary"
            className="bg-primary/10 text-primary border-primary/20"
          >
            Professor Mode
          </Badge>
        </div>
      </header>

      <div className="max-w-6xl mx-auto">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3 lg:w-96">
            <TabsTrigger value="material" className="flex items-center gap-2">
              <File className="h-4 w-4" /> Material
            </TabsTrigger>
            <TabsTrigger value="avatar" className="flex items-center gap-2">
              <CircleUser className="w-4 h-4" /> Avatar
            </TabsTrigger>
            <TabsTrigger value="audio" className="flex items-center gap-2">
              <Volume2 className="h-4 w-4" /> Audio
            </TabsTrigger>
          </TabsList>

          {/* Material Upload Tab (Slides + Videos) */}
          <TabsContent value="material" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Upload your Lecture Material</CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Slides */}
                <FileUpload
                  files={slides}
                  onUpload={handleSlidesUpload}
                  onRemove={handleSlidesRemove}
                  onFilesChange={setSlides}
                  acceptedTypes={["application/pdf"]}
                  maxSize={100}
                  icon={
                    <FileText className="w-12 h-12 text-muted-foreground" />
                  }
                  title="Upload Lecture Slides"
                  description="PDF files only"
                  multiple={true}
                />

                {/* Videos */}
                <FileUpload
                  files={videos}
                  onUpload={handleVideosUpload}
                  onRemove={handleVideosRemove}
                  onFilesChange={setVideos}
                  acceptedTypes={["video/mp4", "video/webm", "video/ogg"]}
                  maxSize={500}
                  icon={<Video className="w-12 h-12 text-muted-foreground" />}
                  title="Upload Lecture Videos"
                  description="MP4, WebM, OGG files only"
                  multiple={false}
                />
              </CardContent>
            </Card>
          </TabsContent>

          {/* Avatar Upload Tab */}
          <TabsContent value="avatar" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Upload your Avatar</CardTitle>
                <CardDescription>
                  To replace an avatar, simply upload a new one.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <AvatarUpload />
              </CardContent>
            </Card>
          </TabsContent>

          {/* Audio Upload Tab */}
          <TabsContent value="audio" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Upload your Audio</CardTitle>
                <CardDescription>To replace an audio, simply upload a new one.</CardDescription>
              </CardHeader>
              <CardContent>
                <AudioUpload />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </main>
  );
}
