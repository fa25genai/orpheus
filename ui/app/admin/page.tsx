"use client";
import {Badge} from "@/components/ui/badge";
import {Button} from "@/components/ui/button";
import {Card, CardContent, CardHeader, CardTitle} from "@/components/ui/card";
import {Tabs, TabsContent, TabsList, TabsTrigger} from "@/components/ui/tabs";
import {
  ArrowLeft,
  CircleUser,
  FileText,
  File,
  ImageIcon,
  Mic,
  Volume2,
} from "lucide-react";
import Link from "next/link";
import {useState} from "react";
import {UploadedFile} from "@/types/uploading";
import {FileUpload} from "@/components/file-upload";

export default function Admin() {
  const [activeTab, setActiveTab] = useState("slides");
  const [uploadedFiles, setUploadedFiles] = useState<{
    slides: UploadedFile[];
    avatar: UploadedFile[];
    audio: UploadedFile[];
  }>({
    slides: [],
    avatar: [],
    audio: [],
  });

  const handleFilesUploaded =
    (type: "slides" | "avatar" | "audio") => (files: UploadedFile[]) => {
      setUploadedFiles((prev) => ({
        ...prev,
        [type]: files,
      }));
    };

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
            <TabsTrigger value="slides" className="flex items-center gap-2">
              <File className="h-4 w-4" />
              Slides
            </TabsTrigger>
            <TabsTrigger value="avatar" className="flex items-center gap-2">
              <CircleUser className="w-4 h-4" />
              Avatar
            </TabsTrigger>
            <TabsTrigger value="audio" className="flex items-center gap-2">
              <Volume2 className="w-4 h-4" />
              Audio
            </TabsTrigger>
          </TabsList>

          {/* Upload Tab */}
          <TabsContent value="slides" className="space-y-6">
            {/* File Upload Section */}
            <Card>
              <CardHeader>
                <CardTitle>Upload your Slides</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  {/* Slides Upload */}
                  <FileUpload
                    acceptedTypes={["application/pdf"]}
                    maxSize={100}
                    onFilesUploaded={handleFilesUploaded("slides")}
                    icon={
                      <FileText className="w-12 h-12 text-muted-foreground" />
                    }
                    title="Upload Lecture Slides"
                    description="PDF files"
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Lectures Tab */}
          <TabsContent value="avatar" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Upload your avatar</CardTitle>
              </CardHeader>
              <CardContent>
                {/* Avatar Image Upload */}
                <FileUpload
                  acceptedTypes={["image/jpeg", "image/png", "image/webp"]}
                  maxSize={10}
                  onFilesUploaded={handleFilesUploaded("avatar")}
                  icon={
                    <ImageIcon className="w-12 h-12 text-muted-foreground" />
                  }
                  title="Professor Avatar Image"
                  description="JPG, PNG, WEBP"
                />
              </CardContent>
            </Card>
          </TabsContent>

          {/* Audio Tab */}
          <TabsContent value="audio" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Upload your audio</CardTitle>
              </CardHeader>
              <CardContent>
                {/* Avatar Image Upload */}
                <FileUpload
                  acceptedTypes={["audio/mpeg", "audio/wav", "audio/mp3"]}
                  maxSize={100}
                  multiple={true}
                  onFilesUploaded={handleFilesUploaded("audio")}
                  icon={<Mic className="w-12 h-12 text-muted-foreground" />}
                  title="Audio Samples"
                  description="MP3, WAV"
                />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </main>
  );
}
